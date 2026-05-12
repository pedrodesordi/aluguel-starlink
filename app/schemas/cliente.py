from __future__ import annotations
import re
from pydantic import BaseModel, field_validator


class ClienteCreate(BaseModel):
    nome: str
    cpf: str
    telefone: str | None = None
    email: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    estado: str | None = None
    observacoes: str | None = None

    @field_validator("cpf")
    @classmethod
    def formatar_cpf(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if len(digits) != 11:
            raise ValueError("CPF deve ter 11 dígitos")
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"

    @field_validator("estado")
    @classmethod
    def estado_upper(cls, v: str | None) -> str | None:
        return v.upper() if v else v


class ClienteUpdate(BaseModel):
    nome: str | None = None
    cpf: str | None = None
    telefone: str | None = None
    email: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    estado: str | None = None
    observacoes: str | None = None
