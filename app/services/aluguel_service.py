from __future__ import annotations
from datetime import date
from decimal import Decimal

from supabase import Client


def calcular_multa_corrente(aluguel: dict) -> Decimal:
    prazo = date.fromisoformat(aluguel["data_fim_prevista"])
    dias = max(0, (date.today() - prazo).days)
    return Decimal(str(aluguel["valor_multa_dia"])) * dias


def calcular_valor_diaria(dias: int, db: Client) -> Decimal | None:
    res = (
        db.table("faixas_preco_diaria")
        .select("valor_por_dia")
        .lte("dias_min", dias)
        .gte("dias_max", dias)
        .eq("ativo", True)
        .execute()
    )
    if res.data:
        return Decimal(str(res.data[0]["valor_por_dia"]))
    return None


def devolver_aluguel(aluguel_id: str, data_devolucao: str, db: Client) -> dict:
    db.table("alugueis").update({
        "data_fim_real": data_devolucao,
        "status": "devolvido",
    }).eq("id", aluguel_id).execute()

    aluguel_atualizado = db.table("alugueis").select("*").eq("id", aluguel_id).execute().data[0]

    multa = float(aluguel_atualizado.get("valor_multa_total") or 0)
    if multa > 0:
        db.table("pagamentos").insert({
            "aluguel_id": aluguel_id,
            "descricao": f"Multa por atraso ({aluguel_atualizado['dias_atraso']} dias)",
            "valor": multa,
            "data_vencimento": data_devolucao,
            "tipo": "multa",
            "status": "pendente",
        }).execute()

    return aluguel_atualizado
