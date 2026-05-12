from __future__ import annotations
from datetime import date
from decimal import Decimal

from supabase import Client


def calcular_multa_corrente(aluguel: dict) -> Decimal:
    prazo = date.fromisoformat(aluguel["data_fim_prevista"])
    dias = max(0, (date.today() - prazo).days)
    return Decimal(str(aluguel["valor_multa_dia"])) * dias


def calcular_valor_diaria(dias: int, db: Client, tipo_plano: str = "100GB") -> Decimal | None:
    # 1. Pacote exato para esse número de dias
    pacote = (
        db.table("pacotes_diaria")
        .select("valor_total")
        .eq("tipo_plano", tipo_plano)
        .eq("dias", dias)
        .eq("ativo", True)
        .execute()
    )
    if pacote.data:
        return Decimal(str(pacote.data[0]["valor_total"])) / dias

    # 2. Faixa base por intervalo
    faixa = (
        db.table("faixas_preco_diaria")
        .select("valor_por_dia")
        .lte("dias_min", dias)
        .gte("dias_max", dias)
        .eq("tipo_plano", tipo_plano)
        .eq("ativo", True)
        .execute()
    )
    if faixa.data:
        return Decimal(str(faixa.data[0]["valor_por_dia"]))

    # 3. Fallback: menor faixa disponível (diária base)
    base = (
        db.table("faixas_preco_diaria")
        .select("valor_por_dia")
        .eq("tipo_plano", tipo_plano)
        .eq("ativo", True)
        .order("dias_min")
        .limit(1)
        .execute()
    )
    return Decimal(str(base.data[0]["valor_por_dia"])) if base.data else None


def tem_pacote_exato(dias: int, db: Client, tipo_plano: str = "100GB") -> float | None:
    res = (
        db.table("pacotes_diaria")
        .select("valor_total")
        .eq("tipo_plano", tipo_plano)
        .eq("dias", dias)
        .eq("ativo", True)
        .execute()
    )
    return float(res.data[0]["valor_total"]) if res.data else None


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
