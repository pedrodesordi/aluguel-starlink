from __future__ import annotations
from pydantic import BaseModel, model_validator


class AluguelCreate(BaseModel):
    cliente_id: str
    equipamento_id: str
    data_inicio: str
    data_fim_prevista: str
    modalidade: str
    valor_contratado: float
    valor_total_previsto: float
    valor_multa_dia: float = 0.0
    observacoes: str | None = None

    @model_validator(mode="after")
    def datas_validas(self):
        if self.data_inicio >= self.data_fim_prevista:
            raise ValueError("Data de fim deve ser posterior à data de início")
        return self


class AluguelUpdate(BaseModel):
    observacoes: str | None = None
    valor_multa_dia: float | None = None
