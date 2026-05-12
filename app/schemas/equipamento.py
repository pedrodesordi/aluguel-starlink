from __future__ import annotations
from pydantic import BaseModel, field_validator


class EquipamentoCreate(BaseModel):
    numero_serie: str
    numero_starlink: str | None = None
    modelo: str
    tipo_plano: str | None = None
    vencimento_mensalidade: int | None = None
    custo_mensalidade: float | None = None
    status: str = "disponivel"
    descricao: str | None = None

    @field_validator("vencimento_mensalidade")
    @classmethod
    def dia_valido(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 31):
            raise ValueError("Dia deve ser entre 1 e 31")
        return v


class EquipamentoUpdate(BaseModel):
    numero_serie: str | None = None
    numero_starlink: str | None = None
    modelo: str | None = None
    tipo_plano: str | None = None
    vencimento_mensalidade: int | None = None
    custo_mensalidade: float | None = None
    status: str | None = None
    descricao: str | None = None
