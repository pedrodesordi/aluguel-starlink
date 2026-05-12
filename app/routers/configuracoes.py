from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from app.templates_config import templates
from pydantic import ValidationError
from supabase import Client

from app.auth import require_admin
from app.database import get_db
from app.schemas.faixa_preco import FaixaPrecoCreate

router = APIRouter(tags=["configuracoes"])


def _flash(request: Request, tipo: str, msg: str):
    request.session["flash"] = {"tipo": tipo, "msg": msg}


@router.get("/faixas-preco")
def listar(request: Request, user: dict = Depends(require_admin), db: Client = Depends(get_db)):
    faixas = db.table("faixas_preco_diaria").select("*").order("dias_min").execute().data
    flash = request.session.pop("flash", None)
    return templates.TemplateResponse("configuracoes/faixas_preco.html", {
        "request": request, "user": user, "faixas": faixas, "flash": flash,
    })


@router.post("/faixas-preco/nova")
def criar(
    request: Request,
    dias_min: int = Form(...), dias_max: int = Form(...), valor_por_dia: float = Form(...),
    user: dict = Depends(require_admin), db: Client = Depends(get_db),
):
    try:
        data = FaixaPrecoCreate(dias_min=dias_min, dias_max=dias_max, valor_por_dia=valor_por_dia)
    except ValidationError as e:
        faixas = db.table("faixas_preco_diaria").select("*").order("dias_min").execute().data
        erros = {err["loc"][0]: err["msg"] for err in e.errors()}
        return templates.TemplateResponse("configuracoes/faixas_preco.html", {
            "request": request, "user": user, "faixas": faixas, "erros": erros,
        }, status_code=422)

    db.table("faixas_preco_diaria").insert(data.model_dump()).execute()
    _flash(request, "success", "Faixa de preço criada!")
    return RedirectResponse("/configuracoes/faixas-preco", status_code=303)


@router.post("/faixas-preco/{id}/excluir")
def excluir(id: str, request: Request, user: dict = Depends(require_admin), db: Client = Depends(get_db)):
    db.table("faixas_preco_diaria").update({"ativo": False}).eq("id", id).execute()
    _flash(request, "success", "Faixa removida.")
    return RedirectResponse("/configuracoes/faixas-preco", status_code=303)
