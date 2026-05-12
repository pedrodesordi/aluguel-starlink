from __future__ import annotations
from pydantic import BaseModel, field_validator


class UsuarioCreate(BaseModel):
    nome: str
    email: str
    senha: str
    perfil: str = "operador"

    @field_validator("perfil")
    @classmethod
    def perfil_valido(cls, v: str) -> str:
        if v not in ("admin", "operador"):
            raise ValueError("Perfil deve ser admin ou operador")
        return v


class UsuarioUpdate(BaseModel):
    nome: str | None = None
    email: str | None = None
    perfil: str | None = None
    ativo: bool | None = None
    senha: str | None = None
