from __future__ import annotations
from pydantic import BaseModel


class PagamentoCreate(BaseModel):
    aluguel_id: str
    descricao: str
    valor: float
    data_vencimento: str
    tipo: str = "mensalidade"
    observacoes: str | None = None
