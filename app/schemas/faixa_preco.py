from pydantic import BaseModel, model_validator


class FaixaPrecoCreate(BaseModel):
    dias_min: int
    dias_max: int
    valor_por_dia: float

    @model_validator(mode="after")
    def faixa_valida(self):
        if self.dias_min > self.dias_max:
            raise ValueError("dias_min deve ser menor ou igual a dias_max")
        if self.dias_min <= 0 or self.valor_por_dia <= 0:
            raise ValueError("dias_min e valor_por_dia devem ser positivos")
        return self
