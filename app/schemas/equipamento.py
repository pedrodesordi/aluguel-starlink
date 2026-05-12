from __future__ import annotations
from pydantic import BaseModel


class EquipamentoCreate(BaseModel):
    numero_serie: str
    numero_starlink: str | None = None
    modelo: str
    tipo_plano: str | None = None
    vencimento_mensalidade: str | None = None
    status: str = "disponivel"
    descricao: str | None = None
    data_aquisicao: str | None = None
    valor_aquisicao: float | None = None


class EquipamentoUpdate(BaseModel):
    numero_serie: str | None = None
    numero_starlink: str | None = None
    modelo: str | None = None
    tipo_plano: str | None = None
    vencimento_mensalidade: str | None = None
    status: str | None = None
    descricao: str | None = None
    data_aquisicao: str | None = None
    valor_aquisicao: float | None = None
