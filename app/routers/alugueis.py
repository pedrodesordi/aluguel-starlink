from datetime import date

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_config import templates
from pydantic import ValidationError
from supabase import Client

from app.auth import get_current_user
from app.database import get_db
from app.schemas.aluguel import AluguelCreate
from app.services.aluguel_service import calcular_multa_corrente, calcular_valor_diaria, devolver_aluguel
from app.services.financeiro_service import gerar_pagamento_diaria, gerar_parcelas_mensais

router = APIRouter(tags=["alugueis"])


def _flash(request: Request, tipo: str, msg: str):
    request.session["flash"] = {"tipo": tipo, "msg": msg}


@router.get("/")
def listar(
    request: Request, status: str = "",
    user: dict = Depends(get_current_user), db: Client = Depends(get_db),
):
    query = (
        db.table("alugueis")
        .select("*,clientes(nome,telefone),equipamentos(modelo,numero_serie)")
        .order("criado_em", desc=True)
    )
    if status:
        query = query.eq("status", status)
    alugueis = query.execute().data

    # Adiciona multa corrente para aluguéis atrasados sem devolução
    for a in alugueis:
        if a["status"] == "atrasado" and not a.get("data_fim_real"):
            a["multa_corrente"] = float(calcular_multa_corrente(a))

    flash = request.session.pop("flash", None)
    return templates.TemplateResponse("alugueis/list.html", {
        "request": request, "user": user, "alugueis": alugueis, "filtro_status": status, "flash": flash,
    })


@router.get("/novo")
def novo_form(request: Request, user: dict = Depends(get_current_user), db: Client = Depends(get_db)):
    clientes = db.table("clientes").select("id,nome").eq("ativo", True).order("nome").execute().data
    equipamentos = db.table("equipamentos").select("id,modelo,numero_serie").eq("status", "disponivel").execute().data
    return templates.TemplateResponse("alugueis/form.html", {
        "request": request, "user": user, "clientes": clientes, "equipamentos": equipamentos, "aluguel": {},
    })


@router.get("/calcular-diaria", response_class=HTMLResponse)
def calcular_diaria(dias: int = Query(...), user: dict = Depends(get_current_user), db: Client = Depends(get_db)):
    valor = calcular_valor_diaria(dias, db)
    if valor:
        return f'<span class="text-success fw-bold">R$ {float(valor):.2f}/dia</span> <input type="hidden" name="_valor_sugerido" value="{float(valor)}">'
    return '<span class="text-warning">Nenhuma faixa cadastrada para este período</span>'


@router.post("/novo")
def criar(
    request: Request,
    cliente_id: str = Form(...), equipamento_id: str = Form(...),
    data_inicio: str = Form(...), data_fim_prevista: str = Form(...),
    modalidade: str = Form(...), valor_contratado: str = Form(...),
    valor_multa_dia: str = Form("0"),
    observacoes: str = Form(""),
    user: dict = Depends(get_current_user), db: Client = Depends(get_db),
):
    try:
        d_inicio = date.fromisoformat(data_inicio)
        d_fim = date.fromisoformat(data_fim_prevista)
        dias = (d_fim - d_inicio).days
        val_contratado = float(valor_contratado)
        val_total = val_contratado * dias if modalidade == "diaria" else val_contratado

        data = AluguelCreate(
            cliente_id=cliente_id, equipamento_id=equipamento_id,
            data_inicio=data_inicio, data_fim_prevista=data_fim_prevista,
            modalidade=modalidade, valor_contratado=val_contratado,
            valor_total_previsto=val_total,
            valor_multa_dia=float(valor_multa_dia) if valor_multa_dia else 0.0,
            observacoes=observacoes or None,
        )
    except (ValidationError, ValueError) as e:
        clientes = db.table("clientes").select("id,nome").eq("ativo", True).order("nome").execute().data
        equipamentos = db.table("equipamentos").select("id,modelo,numero_serie").eq("status", "disponivel").execute().data
        erros = {"geral": str(e)}
        return templates.TemplateResponse("alugueis/form.html", {
            "request": request, "user": user, "clientes": clientes, "equipamentos": equipamentos,
            "aluguel": {}, "erros": erros,
        }, status_code=422)

    res = db.table("alugueis").insert(data.model_dump(exclude_none=True)).execute()
    aluguel = res.data[0]

    # Gera parcelas conforme modalidade
    if modalidade == "mensal":
        gerar_parcelas_mensais(aluguel, db)
    else:
        gerar_pagamento_diaria(aluguel, db)

    # Cria termo de responsabilidade
    db.table("termos_responsabilidade").insert({"aluguel_id": aluguel["id"]}).execute()

    _flash(request, "success", "Aluguel criado com sucesso! Envie o link do termo ao cliente.")
    return RedirectResponse(f"/alugueis/{aluguel['id']}", status_code=303)


@router.get("/{id}")
def detalhe(id: str, request: Request, user: dict = Depends(get_current_user), db: Client = Depends(get_db)):
    aluguel = (
        db.table("alugueis")
        .select("*,clientes(*),equipamentos(*)")
        .eq("id", id)
        .execute()
        .data[0]
    )
    pagamentos = db.table("pagamentos").select("*").eq("aluguel_id", id).order("data_vencimento").execute().data
    termo = db.table("termos_responsabilidade").select("*").eq("aluguel_id", id).execute().data
    termo = termo[0] if termo else None

    multa_corrente = 0.0
    if aluguel["status"] == "atrasado" and not aluguel.get("data_fim_real"):
        multa_corrente = float(calcular_multa_corrente(aluguel))

    flash = request.session.pop("flash", None)
    return templates.TemplateResponse("alugueis/detail.html", {
        "request": request, "user": user, "aluguel": aluguel,
        "pagamentos": pagamentos, "termo": termo,
        "multa_corrente": multa_corrente, "flash": flash,
    })


@router.post("/{id}/devolver")
def devolver(
    id: str, request: Request,
    data_devolucao: str = Form(...),
    user: dict = Depends(get_current_user), db: Client = Depends(get_db),
):
    devolver_aluguel(id, data_devolucao, db)
    _flash(request, "success", "Devolução registrada com sucesso!")
    return RedirectResponse(f"/alugueis/{id}", status_code=303)
