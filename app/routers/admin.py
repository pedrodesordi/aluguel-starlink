from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from app.templates_config import templates
from supabase import Client

from app.auth import hash_password, require_admin
from app.database import get_db
from app.schemas.usuario import UsuarioCreate

router = APIRouter(tags=["admin"])


def _flash(request: Request, tipo: str, msg: str):
    request.session["flash"] = {"tipo": tipo, "msg": msg}


@router.get("/usuarios")
def listar(request: Request, user: dict = Depends(require_admin), db: Client = Depends(get_db)):
    usuarios = db.table("usuarios").select("id,nome,email,perfil,ativo,criado_em").order("nome").execute().data
    flash = request.session.pop("flash", None)
    return templates.TemplateResponse("admin/usuarios.html", {
        "request": request, "user": user, "usuarios": usuarios, "flash": flash,
    })


@router.post("/usuarios/novo")
def criar(
    request: Request,
    nome: str = Form(...), email: str = Form(...),
    senha: str = Form(...), perfil: str = Form("operador"),
    user: dict = Depends(require_admin), db: Client = Depends(get_db),
):
    senha_hash = hash_password(senha)
    db.table("usuarios").insert({"nome": nome, "email": email, "senha_hash": senha_hash, "perfil": perfil}).execute()
    _flash(request, "success", f"Usuário {nome} criado com sucesso!")
    return RedirectResponse("/admin/usuarios", status_code=303)


@router.post("/usuarios/{id}/editar")
def editar(
    id: str, request: Request,
    nome: str = Form(...), email: str = Form(...),
    perfil: str = Form("operador"), nova_senha: str = Form(""),
    user: dict = Depends(require_admin), db: Client = Depends(get_db),
):
    payload = {"nome": nome, "email": email, "perfil": perfil}
    if nova_senha:
        payload["senha_hash"] = hash_password(nova_senha)
    db.table("usuarios").update(payload).eq("id", id).execute()
    _flash(request, "success", "Usuário atualizado!")
    return RedirectResponse("/admin/usuarios", status_code=303)


@router.post("/usuarios/{id}/desativar")
def desativar(id: str, request: Request, user: dict = Depends(require_admin), db: Client = Depends(get_db)):
    if id == user["id"]:
        _flash(request, "danger", "Você não pode desativar sua própria conta.")
        return RedirectResponse("/admin/usuarios", status_code=303)
    db.table("usuarios").update({"ativo": False}).eq("id", id).execute()
    _flash(request, "warning", "Usuário desativado.")
    return RedirectResponse("/admin/usuarios", status_code=303)


@router.post("/usuarios/{id}/reativar")
def reativar(id: str, request: Request, user: dict = Depends(require_admin), db: Client = Depends(get_db)):
    db.table("usuarios").update({"ativo": True}).eq("id", id).execute()
    _flash(request, "success", "Usuário reativado.")
    return RedirectResponse("/admin/usuarios", status_code=303)
