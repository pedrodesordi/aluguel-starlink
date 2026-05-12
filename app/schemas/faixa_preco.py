from pydantic import BaseModel, field_validator, model_validator

PLANOS_VALIDOS = {"100GB", "ILIMITADO"}


class FaixaPrecoCreate(BaseModel):
    dias_min: int
    dias_max: int
    valor_por_dia: float
    tipo_plano: str = "100GB"

    @field_validator("tipo_plano")
    @classmethod
    def plano_valido(cls, v: str) -> str:
        if v not in PLANOS_VALIDOS:
            raise ValueError(f"Plano inválido. Use: {sorted(PLANOS_VALIDOS)}")
        return v

    @model_validator(mode="after")
    def faixa_valida(self):
        if self.dias_min > self.dias_max:
            raise ValueError("dias_min deve ser menor ou igual a dias_max")
        if self.dias_min <= 0 or self.valor_por_dia <= 0:
            raise ValueError("dias_min e valor_por_dia devem ser positivos")
        return self
