from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from app.templates_config import templates
from pydantic import ValidationError
from supabase import Client

from app.auth import get_current_user
from app.database import get_db
from app.schemas.cliente import ClienteCreate, ClienteUpdate

router = APIRouter(tags=["clientes"])


def _flash(request: Request, tipo: str, msg: str):
    request.session["flash"] = {"tipo": tipo, "msg": msg}


@router.get("/")
def listar(request: Request, nome: str = "", user: dict = Depends(get_current_user), db: Client = Depends(get_db)):
    query = db.table("clientes").select("*").eq("ativo", True).order("nome")
    if nome:
        query = query.ilike("nome", f"%{nome}%")
    clientes = query.execute().data
    flash = request.session.pop("flash", None)
    return templates.TemplateResponse("clientes/list.html", {
        "request": request, "user": user, "clientes": clientes, "filtro_nome": nome, "flash": flash,
    })


@router.get("/novo")
def novo_form(request: Request, user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("clientes/form.html", {"request": request, "user": user, "cliente": {}})


@router.post("/novo")
def criar(
    request: Request,
    nome: str = Form(...), cpf: str = Form(...), telefone: str = Form(""),
    email: str = Form(""), endereco: str = Form(""), cidade: str = Form(""),
    estado: str = Form(""), observacoes: str = Form(""),
    user: dict = Depends(get_current_user), db: Client = Depends(get_db),
):
    try:
        data = ClienteCreate(nome=nome, cpf=cpf, telefone=telefone or None, email=email or None,
                             endereco=endereco or None, cidade=cidade or None,
                             estado=estado or None, observacoes=observacoes or None)
    except ValidationError as e:
        erros = {err["loc"][0]: err["msg"] for err in e.errors()}
        return templates.TemplateResponse("clientes/form.html", {
            "request": request, "user": user,
            "cliente": {"nome": nome, "cpf": cpf, "telefone": telefone, "email": email,
                        "endereco": endereco, "cidade": cidade, "estado": estado, "observacoes": observacoes},
            "erros": erros,
        }, status_code=422)

    db.table("clientes").insert(data.model_dump(exclude_none=True)).execute()
    _flash(request, "success", f"Cliente {nome} cadastrado com sucesso!")
    return RedirectResponse("/clientes/", status_code=303)


@router.get("/{id}")
def detalhe(id: str, request: Request, user: dict = Depends(get_current_user), db: Client = Depends(get_db)):
    cliente = db.table("clientes").select("*").eq("id", id).execute().data[0]
    alugueis = (
        db.table("alugueis")
        .select("*,equipamentos(modelo,numero_serie)")
        .eq("cliente_id", id)
        .order("criado_em", desc=True)
        .execute()
        .data
    )
    flash = request.session.pop("flash", None)
    return templates.TemplateResponse("clientes/detail.html", {
        "request": request, "user": user, "cliente": cliente, "alugueis": alugueis, "flash": flash,
    })


@router.get("/{id}/editar")
def editar_form(id: str, request: Request, user: dict = Depends(get_current_user), db: Client = Depends(get_db)):
    cliente = db.table("clientes").select("*").eq("id", id).execute().data[0]
    return templates.TemplateResponse("clientes/form.html", {"request": request, "user": user, "cliente": cliente})


@router.post("/{id}/editar")
def editar(
    id: str, request: Request,
    nome: str = Form(...), cpf: str = Form(...), telefone: str = Form(""),
    email: str = Form(""), endereco: str = Form(""), cidade: str = Form(""),
    estado: str = Form(""), observacoes: str = Form(""),
    user: dict = Depends(get_current_user), db: Client = Depends(get_db),
):
    try:
        data = ClienteCreate(nome=nome, cpf=cpf, telefone=telefone or None, email=email or None,
                             endereco=endereco or None, cidade=cidade or None,
                             estado=estado or None, observacoes=observacoes or None)
    except ValidationError as e:
        erros = {err["loc"][0]: err["msg"] for err in e.errors()}
        return templates.TemplateResponse("clientes/form.html", {
            "request": request, "user": user,
            "cliente": {"id": id, "nome": nome, "cpf": cpf, "telefone": telefone, "email": email,
                        "endereco": endereco, "cidade": cidade, "estado": estado, "observacoes": observacoes},
            "erros": erros,
        }, status_code=422)

    db.table("clientes").update(data.model_dump(exclude_none=True)).eq("id", id).execute()
    _flash(request, "success", "Cliente atualizado com sucesso!")
    return RedirectResponse(f"/clientes/{id}", status_code=303)


@router.post("/{id}/excluir")
def excluir(id: str, request: Request, user: dict = Depends(get_current_user), db: Client = Depends(get_db)):
    db.table("clientes").update({"ativo": False}).eq("id", id).execute()
    _flash(request, "success", "Cliente removido.")
    return RedirectResponse("/clientes/", status_code=303)
