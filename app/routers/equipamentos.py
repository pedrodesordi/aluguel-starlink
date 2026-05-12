from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from supabase import Client

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.schemas.equipamento import EquipamentoCreate

router = APIRouter(tags=["equipamentos"])
templates = Jinja2Templates(directory="app/templates")


def _flash(request: Request, tipo: str, msg: str):
    request.session["flash"] = {"tipo": tipo, "msg": msg}


@router.get("/")
def listar(
    request: Request, status: str = "", modelo: str = "",
    user: dict = Depends(get_current_user), db: Client = Depends(get_db),
):
    query = db.table("equipamentos").select("*").order("modelo")
    if status:
        query = query.eq("status", status)
    if modelo:
        query = query.ilike("modelo", f"%{modelo}%")
    equipamentos = query.execute().data
    flash = request.session.pop("flash", None)
    return templates.TemplateResponse("equipamentos/list.html", {
        "request": request, "user": user, "equipamentos": equipamentos,
        "filtro_status": status, "filtro_modelo": modelo, "flash": flash,
    })


@router.get("/novo")
def novo_form(request: Request, user: dict = Depends(require_admin)):
    return templates.TemplateResponse("equipamentos/form.html", {"request": request, "user": user, "equipamento": {}})


@router.post("/novo")
def criar(
    request: Request,
    numero_serie: str = Form(...), numero_starlink: str = Form(""),
    modelo: str = Form(...), tipo_plano: str = Form(""),
    vencimento_mensalidade: str = Form(""), status: str = Form("disponivel"),
    descricao: str = Form(""), data_aquisicao: str = Form(""),
    valor_aquisicao: str = Form(""),
    user: dict = Depends(require_admin), db: Client = Depends(get_db),
):
    try:
        data = EquipamentoCreate(
            numero_serie=numero_serie, numero_starlink=numero_starlink or None,
            modelo=modelo, tipo_plano=tipo_plano or None,
            vencimento_mensalidade=vencimento_mensalidade or None, status=status,
            descricao=descricao or None, data_aquisicao=data_aquisicao or None,
            valor_aquisicao=float(valor_aquisicao) if valor_aquisicao else None,
        )
    except (ValidationError, ValueError) as e:
        erros = {}
        if isinstance(e, ValidationError):
            erros = {err["loc"][0]: err["msg"] for err in e.errors()}
        return templates.TemplateResponse("equipamentos/form.html", {
            "request": request, "user": user,
            "equipamento": {"numero_serie": numero_serie, "modelo": modelo},
            "erros": erros,
        }, status_code=422)

    db.table("equipamentos").insert(data.model_dump(exclude_none=True)).execute()
    _flash(request, "success", f"Equipamento {numero_serie} cadastrado!")
    return RedirectResponse("/equipamentos/", status_code=303)


@router.get("/{id}/editar")
def editar_form(id: str, request: Request, user: dict = Depends(require_admin), db: Client = Depends(get_db)):
    equipamento = db.table("equipamentos").select("*").eq("id", id).execute().data[0]
    return templates.TemplateResponse("equipamentos/form.html", {
        "request": request, "user": user, "equipamento": equipamento,
    })


@router.post("/{id}/editar")
def editar(
    id: str, request: Request,
    numero_serie: str = Form(...), numero_starlink: str = Form(""),
    modelo: str = Form(...), tipo_plano: str = Form(""),
    vencimento_mensalidade: str = Form(""), status: str = Form("disponivel"),
    descricao: str = Form(""), data_aquisicao: str = Form(""),
    valor_aquisicao: str = Form(""),
    user: dict = Depends(require_admin), db: Client = Depends(get_db),
):
    payload = {
        "numero_serie": numero_serie,
        "numero_starlink": numero_starlink or None,
        "modelo": modelo,
        "tipo_plano": tipo_plano or None,
        "vencimento_mensalidade": vencimento_mensalidade or None,
        "status": status,
        "descricao": descricao or None,
        "data_aquisicao": data_aquisicao or None,
        "valor_aquisicao": float(valor_aquisicao) if valor_aquisicao else None,
    }
    db.table("equipamentos").update({k: v for k, v in payload.items() if v is not None}).eq("id", id).execute()
    _flash(request, "success", "Equipamento atualizado!")
    return RedirectResponse("/equipamentos/", status_code=303)
