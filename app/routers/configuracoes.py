from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from app.templates_config import templates
from pydantic import ValidationError
from supabase import Client

from app.auth import require_admin
from app.database import get_db
from app.schemas.faixa_preco import FaixaPrecoCreate, PacoteCreate

router = APIRouter(tags=["configuracoes"])


def _flash(request: Request, tipo: str, msg: str):
    request.session["flash"] = {"tipo": tipo, "msg": msg}


def _get_dados(db: Client):
    faixas_100gb = db.table("faixas_preco_diaria").select("*").eq("tipo_plano", "100GB").eq("ativo", True).order("dias_min").execute().data
    faixas_ilimitado = db.table("faixas_preco_diaria").select("*").eq("tipo_plano", "ILIMITADO").eq("ativo", True).order("dias_min").execute().data
    pacotes_100gb = db.table("pacotes_diaria").select("*").eq("tipo_plano", "100GB").eq("ativo", True).order("dias").execute().data
    pacotes_ilimitado = db.table("pacotes_diaria").select("*").eq("tipo_plano", "ILIMITADO").eq("ativo", True).order("dias").execute().data
    return faixas_100gb, faixas_ilimitado, pacotes_100gb, pacotes_ilimitado


@router.get("/faixas-preco")
def listar(request: Request, user: dict = Depends(require_admin), db: Client = Depends(get_db)):
    faixas_100gb, faixas_ilimitado, pacotes_100gb, pacotes_ilimitado = _get_dados(db)
    flash = request.session.pop("flash", None)
    return templates.TemplateResponse("configuracoes/faixas_preco.html", {
        "request": request, "user": user, "flash": flash,
        "faixas_100gb": faixas_100gb, "faixas_ilimitado": faixas_ilimitado,
        "pacotes_100gb": pacotes_100gb, "pacotes_ilimitado": pacotes_ilimitado,
    })


@router.post("/faixas-preco/nova")
def criar_faixa(
    request: Request,
    dias_min: int = Form(...), dias_max: int = Form(...), valor_por_dia: float = Form(...),
    tipo_plano: str = Form("100GB"),
    user: dict = Depends(require_admin), db: Client = Depends(get_db),
):
    try:
        data = FaixaPrecoCreate(dias_min=dias_min, dias_max=dias_max, valor_por_dia=valor_por_dia, tipo_plano=tipo_plano)
    except ValidationError as e:
        faixas_100gb, faixas_ilimitado, pacotes_100gb, pacotes_ilimitado = _get_dados(db)
        erros = {err["loc"][0]: err["msg"] for err in e.errors()}
        return templates.TemplateResponse("configuracoes/faixas_preco.html", {
            "request": request, "user": user,
            "faixas_100gb": faixas_100gb, "faixas_ilimitado": faixas_ilimitado,
            "pacotes_100gb": pacotes_100gb, "pacotes_ilimitado": pacotes_ilimitado,
            "erros": erros,
        }, status_code=422)

    db.table("faixas_preco_diaria").insert(data.model_dump()).execute()
    _flash(request, "success", "Faixa de preço criada!")
    return RedirectResponse("/configuracoes/faixas-preco", status_code=303)


@router.post("/faixas-preco/{id}/excluir")
def excluir_faixa(id: str, request: Request, user: dict = Depends(require_admin), db: Client = Depends(get_db)):
    db.table("faixas_preco_diaria").update({"ativo": False}).eq("id", id).execute()
    _flash(request, "success", "Faixa removida.")
    return RedirectResponse("/configuracoes/faixas-preco", status_code=303)


@router.post("/faixas-preco/pacotes/novo")
def criar_pacote(
    request: Request,
    dias: int = Form(...), valor_total: float = Form(...), tipo_plano: str = Form("100GB"),
    user: dict = Depends(require_admin), db: Client = Depends(get_db),
):
    try:
        data = PacoteCreate(dias=dias, valor_total=valor_total, tipo_plano=tipo_plano)
    except ValidationError as e:
        faixas_100gb, faixas_ilimitado, pacotes_100gb, pacotes_ilimitado = _get_dados(db)
        erros = {err["loc"][0]: err["msg"] for err in e.errors()}
        return templates.TemplateResponse("configuracoes/faixas_preco.html", {
            "request": request, "user": user,
            "faixas_100gb": faixas_100gb, "faixas_ilimitado": faixas_ilimitado,
            "pacotes_100gb": pacotes_100gb, "pacotes_ilimitado": pacotes_ilimitado,
            "erros_pacote": erros,
        }, status_code=422)

    db.table("pacotes_diaria").insert(data.model_dump()).execute()
    _flash(request, "success", f"Pacote de {dias} dias criado!")
    return RedirectResponse("/configuracoes/faixas-preco", status_code=303)


@router.post("/faixas-preco/pacotes/{id}/excluir")
def excluir_pacote(id: str, request: Request, user: dict = Depends(require_admin), db: Client = Depends(get_db)):
    db.table("pacotes_diaria").update({"ativo": False}).eq("id", id).execute()
    _flash(request, "success", "Pacote removido.")
    return RedirectResponse("/configuracoes/faixas-preco", status_code=303)
