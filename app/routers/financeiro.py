from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_config import templates
from supabase import Client

from app.auth import require_admin
from app.database import get_db

router = APIRouter(tags=["financeiro"])


def _flash(request: Request, tipo: str, msg: str):
    request.session["flash"] = {"tipo": tipo, "msg": msg}


@router.get("/")
def listar(
    request: Request, status: str = "", tipo: str = "", mes: str = "",
    user: dict = Depends(require_admin), db: Client = Depends(get_db),
):
    query = (
        db.table("pagamentos")
        .select("*,alugueis(cliente_id,clientes(nome),equipamentos(modelo,numero_serie))")
        .order("data_vencimento", desc=True)
    )
    if status:
        query = query.eq("status", status)
    if tipo:
        query = query.eq("tipo", tipo)
    if mes:
        ano, m = mes.split("-")
        query = query.gte("data_vencimento", f"{ano}-{m}-01").lt("data_vencimento", f"{ano}-{int(m)+1:02d}-01")
    pagamentos = query.execute().data
    flash = request.session.pop("flash", None)
    return templates.TemplateResponse("financeiro/list.html", {
        "request": request, "user": user, "pagamentos": pagamentos,
        "filtro_status": status, "filtro_tipo": tipo, "filtro_mes": mes, "flash": flash,
    })


@router.post("/pagamentos/{id}/pagar", response_class=HTMLResponse)
def marcar_pago(
    id: str, request: Request,
    forma_pagamento: str = Form(None),
    user: dict = Depends(require_admin), db: Client = Depends(get_db),
):
    update_data: dict = {"status": "pago", "data_pagamento": str(date.today())}
    if forma_pagamento:
        update_data["forma_pagamento"] = forma_pagamento
    db.table("pagamentos").update(update_data).eq("id", id).execute()
    forma_labels = {"pix": "PIX", "cartao": "Cartão", "dinheiro": "Dinheiro"}
    forma_label = forma_labels.get(forma_pagamento or "", "")
    extra = f' <span class="text-muted small">{forma_label}</span>' if forma_label else ""
    estornar = (
        f'<button class="btn btn-xs btn-outline-warning ms-1"'
        f' hx-post="/financeiro/pagamentos/{id}/estornar"'
        f' hx-target="#status-pag-{id}" hx-swap="innerHTML"'
        f' hx-confirm="Reverter pagamento para aberto?">'
        f'<i class="bi bi-arrow-counterclockwise"></i></button>'
    )
    return HTMLResponse(f'<span class="badge bg-success">Pago</span>{extra}{estornar}')


@router.post("/pagamentos/{id}/estornar", response_class=HTMLResponse)
def estornar_pagamento(
    id: str, request: Request,
    user: dict = Depends(require_admin), db: Client = Depends(get_db),
):
    db.table("pagamentos").update({
        "status": "pendente",
        "data_pagamento": None,
        "forma_pagamento": None,
    }).eq("id", id).execute()
    pagar_btn = (
        f'<button class="btn btn-xs btn-outline-success ms-1"'
        f' data-bs-toggle="modal" data-bs-target="#modalPagar"'
        f' data-pag-id="{id}" data-pag-target="status-pag-{id}">'
        f'<i class="bi bi-check2"></i> Pagar</button>'
    )
    return HTMLResponse(f'<span class="badge status-pag-pendente">Pendente</span>{pagar_btn}')


@router.get("/relatorio")
def relatorio(
    request: Request, ano: int = date.today().year,
    user: dict = Depends(require_admin), db: Client = Depends(get_db),
):
    meses = []
    for m in range(1, 13):
        inicio = f"{ano}-{m:02d}-01"
        fim = f"{ano}-{m+1:02d}-01" if m < 12 else f"{ano+1}-01-01"
        pags = db.table("pagamentos").select("valor,status").gte("data_vencimento", inicio).lt("data_vencimento", fim).execute().data
        recebido = sum(p["valor"] for p in pags if p["status"] == "pago")
        pendente = sum(p["valor"] for p in pags if p["status"] in ("pendente", "vencido"))
        meses.append({"mes": m, "recebido": recebido, "pendente": pendente, "total": recebido + pendente})

    return templates.TemplateResponse("financeiro/relatorio.html", {
        "request": request, "user": user, "meses": meses, "ano": ano,
    })
