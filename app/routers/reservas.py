from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from app.templates_config import templates
from supabase import Client

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.schemas.aluguel import AluguelCreate
from app.services.aluguel_service import calcular_valor_diaria, tem_pacote_exato
from app.services.financeiro_service import gerar_pagamento_diaria, gerar_parcelas_mensais

router = APIRouter(tags=["reservas"])


def _flash(request: Request, tipo: str, msg: str):
    request.session["flash"] = {"tipo": tipo, "msg": msg}


def _check_expiry(reserva: dict, db: Client) -> bool:
    """Retorna True se expirada (e atualiza status no banco)."""
    expira = reserva.get("expira_em", "")
    if expira and datetime.now(timezone.utc).isoformat() > expira:
        db.table("reservas").update({"status": "expirada"}).eq("id", reserva["id"]).execute()
        return True
    return False


# ─── Rotas públicas (sem auth) ────────────────────────────────────────────────

@router.get("/reservar/buscar-cliente")
def buscar_cliente_por_cpf(cpf: str = Query(...), db: Client = Depends(get_db)):
    cpf_limpo = "".join(c for c in cpf if c.isdigit())
    res = db.table("clientes").select("nome,telefone,email,endereco,cidade,estado").eq("cpf", cpf_limpo).execute()
    if not res.data:
        return JSONResponse({})
    c = res.data[0]
    return JSONResponse({k: v for k, v in c.items() if v is not None})


@router.get("/reservar/calcular-preco", response_class=HTMLResponse)
def calcular_preco_publico(
    dias: int = Query(...), tipo_plano: str = Query("100GB"),
    db: Client = Depends(get_db),
):
    total_pacote = tem_pacote_exato(dias, db, tipo_plano)
    if total_pacote is not None:
        valor_dia = total_pacote / dias
        return (
            f'<span class="text-success fw-bold">Pacote {dias} dias = R$ {total_pacote:.2f} total</span>'
            f' <input type="hidden" id="valor_sugerido" value="{valor_dia:.4f}">'
            f' <input type="hidden" id="valor_total_sugerido" value="{total_pacote:.2f}">'
        )
    valor = calcular_valor_diaria(dias, db, tipo_plano)
    if valor:
        total = float(valor) * dias
        return (
            f'<span class="text-success fw-bold">R$ {float(valor):.2f}/dia = R$ {total:.2f} total</span>'
            f' <input type="hidden" id="valor_sugerido" value="{float(valor):.4f}">'
            f' <input type="hidden" id="valor_total_sugerido" value="{total:.2f}">'
        )
    return '<span class="text-warning">Nenhuma faixa cadastrada para este período</span>'


@router.get("/reservar/{token}")
def form_reserva(token: str, request: Request, db: Client = Depends(get_db)):
    res = db.table("reservas").select("*,equipamentos(*)").eq("token", token).execute()
    if not res.data:
        return templates.TemplateResponse("reservas/expirado.html", {"request": request}, status_code=404)

    reserva = res.data[0]

    if reserva["status"] in ("confirmada", "cancelada"):
        return templates.TemplateResponse("reservas/expirado.html", {"request": request})

    if _check_expiry(reserva, db) or reserva["status"] == "expirada":
        return templates.TemplateResponse("reservas/expirado.html", {"request": request})

    return templates.TemplateResponse("reservas/form.html", {
        "request": request,
        "reserva": reserva,
        "equipamento": reserva["equipamentos"],
        "erros": {},
    })


@router.post("/reservar/{token}")
def submeter_reserva(
    token: str, request: Request,
    nome: str = Form(...), cpf: str = Form(...),
    telefone: str = Form(...), email: str = Form(""),
    endereco: str = Form(""), cidade: str = Form(""), estado: str = Form(""),
    tipo_plano: str = Form(...),
    data_inicio: str = Form(...), data_fim_prevista: str = Form(...),
    previsao_retirada_data: str = Form(...), previsao_retirada_hora: str = Form("08:00"),
    observacoes: str = Form(""),
    db: Client = Depends(get_db),
):
    res = db.table("reservas").select("*,equipamentos(*)").eq("token", token).execute()
    if not res.data:
        return templates.TemplateResponse("reservas/expirado.html", {"request": request}, status_code=404)

    reserva = res.data[0]

    if reserva["status"] != "aguardando" or _check_expiry(reserva, db):
        return templates.TemplateResponse("reservas/expirado.html", {"request": request})

    if not telefone.strip():
        return templates.TemplateResponse("reservas/form.html", {
            "request": request, "reserva": reserva, "equipamento": reserva["equipamentos"],
            "erros": {"telefone": "Telefone / WhatsApp é obrigatório."},
        }, status_code=422)

    from datetime import date as date_type
    try:
        d_inicio = date_type.fromisoformat(data_inicio)
        d_fim = date_type.fromisoformat(data_fim_prevista)
        dias = (d_fim - d_inicio).days
        if dias <= 0:
            raise ValueError("Data de fim deve ser posterior à data de início")
    except ValueError as e:
        return templates.TemplateResponse("reservas/form.html", {
            "request": request, "reserva": reserva, "equipamento": reserva["equipamentos"],
            "erros": {"datas": str(e)},
        }, status_code=422)

    # Verificar sobreposição com aluguéis existentes
    conflito_aluguel = (
        db.table("alugueis").select("id")
        .eq("equipamento_id", reserva["equipamento_id"])
        .in_("status", ["ativo", "atrasado"])
        .lt("data_inicio", data_fim_prevista)
        .gt("data_fim_prevista", data_inicio)
        .execute()
    )
    conflito_reserva = (
        db.table("reservas").select("id")
        .eq("equipamento_id", reserva["equipamento_id"])
        .in_("status", ["preenchida", "confirmada"])
        .neq("id", reserva["id"])
        .lt("data_inicio", data_fim_prevista)
        .gt("data_fim_prevista", data_inicio)
        .execute()
    )
    if conflito_aluguel.data or conflito_reserva.data:
        return templates.TemplateResponse("reservas/form.html", {
            "request": request, "reserva": reserva, "equipamento": reserva["equipamentos"],
            "erros": {"datas": "Equipamento já está reservado ou alugado para este período. Escolha outras datas."},
        }, status_code=422)

    total_pacote = tem_pacote_exato(dias, db, tipo_plano)
    if total_pacote is not None:
        valor_contratado = total_pacote / dias
        valor_total = total_pacote
    else:
        valor_dia = calcular_valor_diaria(dias, db, tipo_plano)
        valor_contratado = float(valor_dia) if valor_dia else 0.0
        valor_total = valor_contratado * dias

    previsao_retirada = f"{previsao_retirada_data}T{previsao_retirada_hora}:00" if previsao_retirada_data else None

    db.table("reservas").update({
        "status": "preenchida",
        "nome_cliente": nome,
        "cpf_cliente": cpf,
        "telefone_cliente": telefone,
        "email_cliente": email or None,
        "endereco_cliente": endereco or None,
        "cidade_cliente": cidade or None,
        "estado_cliente": estado or None,
        "tipo_plano": tipo_plano,
        "data_inicio": data_inicio,
        "data_fim_prevista": data_fim_prevista,
        "valor_contratado": valor_contratado,
        "valor_total_previsto": valor_total,
        "previsao_retirada": previsao_retirada,
        "observacoes": observacoes or None,
    }).eq("token", token).execute()

    return RedirectResponse(f"/reservar/{token}/confirmado", status_code=303)


@router.get("/reservar/{token}/confirmado")
def reserva_confirmada(token: str, request: Request, db: Client = Depends(get_db)):
    res = db.table("reservas").select("*").eq("token", token).execute()
    if not res.data or res.data[0]["status"] not in ("preenchida", "confirmada"):
        return templates.TemplateResponse("reservas/expirado.html", {"request": request})
    return templates.TemplateResponse("reservas/confirmado.html", {
        "request": request, "reserva": res.data[0],
    })


# ─── Rotas admin ──────────────────────────────────────────────────────────────

@router.post("/reservas/gerar/{equipamento_id}")
def gerar_link(
    equipamento_id: str, request: Request,
    user: dict = Depends(get_current_user), db: Client = Depends(get_db),
):
    res = db.table("reservas").insert({"equipamento_id": equipamento_id}).execute()
    token = res.data[0]["token"]
    _flash(request, "success", f"LINK:{token}")
    return RedirectResponse("/reservas/", status_code=303)


@router.get("/reservas/")
def listar_reservas(
    request: Request,
    user: dict = Depends(get_current_user), db: Client = Depends(get_db),
):
    reservas = (
        db.table("reservas")
        .select("*,equipamentos(modelo,numero_serie)")
        .order("criado_em", desc=True)
        .execute()
        .data
    )
    flash = request.session.pop("flash", None)
    novo_link = None
    if flash and flash.get("msg", "").startswith("LINK:"):
        token = flash["msg"].split("LINK:")[1]
        novo_link = token
        flash = None
    return templates.TemplateResponse("reservas/admin_list.html", {
        "request": request, "user": user,
        "reservas": reservas, "novo_link": novo_link, "flash": flash,
    })


@router.post("/reservas/{id}/confirmar")
def confirmar_reserva(
    id: str, request: Request,
    user: dict = Depends(get_current_user), db: Client = Depends(get_db),
):
    reserva = db.table("reservas").select("*").eq("id", id).execute().data[0]

    # Upsert cliente por CPF
    cliente_data = {
        "nome": reserva["nome_cliente"],
        "cpf": reserva["cpf_cliente"],
        "telefone": reserva.get("telefone_cliente"),
        "email": reserva.get("email_cliente"),
        "endereco": reserva.get("endereco_cliente"),
        "cidade": reserva.get("cidade_cliente"),
        "estado": reserva.get("estado_cliente"),
    }
    cliente_res = db.table("clientes").upsert(
        {k: v for k, v in cliente_data.items() if v is not None},
        on_conflict="cpf",
    ).execute()
    cliente_id = cliente_res.data[0]["id"]

    from datetime import date as date_type
    d_inicio = date_type.fromisoformat(str(reserva["data_inicio"]))
    d_fim = date_type.fromisoformat(str(reserva["data_fim_prevista"]))
    dias = (d_fim - d_inicio).days
    val_contratado = float(reserva["valor_contratado"])
    val_total = float(reserva["valor_total_previsto"])

    aluguel_data = AluguelCreate(
        cliente_id=cliente_id,
        equipamento_id=reserva["equipamento_id"],
        data_inicio=str(reserva["data_inicio"]),
        data_fim_prevista=str(reserva["data_fim_prevista"]),
        modalidade="diaria",
        valor_contratado=val_contratado,
        valor_total_previsto=val_total,
        observacoes=reserva.get("observacoes"),
    )
    aluguel = db.table("alugueis").insert(aluguel_data.model_dump(exclude_none=True)).execute().data[0]

    gerar_pagamento_diaria(aluguel, db)
    db.table("termos_responsabilidade").insert({"aluguel_id": aluguel["id"]}).execute()

    db.table("reservas").update({
        "status": "confirmada",
        "aluguel_id": aluguel["id"],
    }).eq("id", id).execute()

    _flash(request, "success", "Reserva confirmada! Aluguel criado com sucesso.")
    return RedirectResponse(f"/alugueis/{aluguel['id']}", status_code=303)


@router.post("/reservas/{id}/excluir")
def excluir_reserva(
    id: str, request: Request,
    user: dict = Depends(require_admin), db: Client = Depends(get_db),
):
    db.table("reservas").delete().eq("id", id).execute()
    _flash(request, "success", "Reserva excluída.")
    return RedirectResponse("/reservas/", status_code=303)


@router.post("/reservas/{id}/cancelar")
def cancelar_reserva(
    id: str, request: Request,
    user: dict = Depends(require_admin), db: Client = Depends(get_db),
):
    db.table("reservas").update({"status": "cancelada"}).eq("id", id).execute()
    _flash(request, "success", "Reserva cancelada.")
    return RedirectResponse("/reservas/", status_code=303)
