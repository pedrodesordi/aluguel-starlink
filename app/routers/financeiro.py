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
    user: dict = Depends(require_admin), db: Client = Depends(get_db),
):
    db.table("pagamentos").update({"status": "pago", "data_pagamento": str(date.today())}).eq("id", id).execute()
    pag = db.table("pagamentos").select("*").eq("id", id).execute().data[0]
    # Retorna HTML parcial para HTMX atualizar a linha
    badge = '<span class="badge bg-success">Pago</span>'
    return HTMLResponse(badge)


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
