import bcrypt
from fastapi import Depends, Request
from app.database import get_db
from supabase import Client


class NaoAutenticado(Exception):
    pass


class SemPermissao(Exception):
    pass


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def get_current_user(request: Request, db: Client = Depends(get_db)) -> dict:
    user_id = request.session.get("user_id")
    if not user_id:
        raise NaoAutenticado()
    res = db.table("usuarios").select("id,nome,email,perfil,ativo").eq("id", user_id).eq("ativo", True).execute()
    if not res.data:
        request.session.clear()
        raise NaoAutenticado()
    return res.data[0]


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["perfil"] != "admin":
        raise SemPermissao()
    return user
