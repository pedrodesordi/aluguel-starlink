from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from app.templates_config import templates
from supabase import Client

from app.auth import hash_password, verify_password
from app.database import get_db

router = APIRouter(tags=["auth"])


@router.get("/login")
def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
def login(request: Request, email: str = Form(...), senha: str = Form(...), db: Client = Depends(get_db)):
    res = db.table("usuarios").select("*").eq("email", email).eq("ativo", True).execute()
    user = res.data[0] if res.data else None
    if not user or not verify_password(senha, user["senha_hash"]):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "erro": "Email ou senha inválidos"},
            status_code=401,
        )
    request.session["user_id"] = user["id"]
    request.session["flash"] = {"tipo": "success", "msg": f"Bem-vindo, {user['nome']}!"}
    return RedirectResponse("/", status_code=302)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)
