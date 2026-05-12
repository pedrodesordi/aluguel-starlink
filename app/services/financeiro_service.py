import calendar
from datetime import date

from supabase import Client


def _proximo_mes(d: date) -> date:
    if d.month == 12:
        return d.replace(year=d.year + 1, month=1)
    novo_mes = d.month + 1
    ultimo_dia = calendar.monthrange(d.year, novo_mes)[1]
    return d.replace(month=novo_mes, day=min(d.day, ultimo_dia))


def gerar_parcelas_mensais(aluguel: dict, db: Client) -> None:
    inicio = date.fromisoformat(aluguel["data_inicio"])
    fim = date.fromisoformat(aluguel["data_fim_prevista"])
    parcelas = []
    cursor = inicio
    i = 1
    while cursor <= fim:
        parcelas.append({
            "aluguel_id": aluguel["id"],
            "descricao": f"Mensalidade {cursor.strftime('%m/%Y')} - Parcela {i}",
            "valor": float(aluguel["valor_contratado"]),
            "data_vencimento": str(cursor),
            "status": "pendente",
            "tipo": "mensalidade",
        })
        cursor = _proximo_mes(cursor)
        i += 1
    if parcelas:
        db.table("pagamentos").insert(parcelas).execute()


def gerar_pagamento_diaria(aluguel: dict, db: Client) -> None:
    db.table("pagamentos").insert({
        "aluguel_id": aluguel["id"],
        "descricao": f"Aluguel diário — {aluguel['data_inicio']} a {aluguel['data_fim_prevista']}",
        "valor": float(aluguel["valor_total_previsto"]),
        "data_vencimento": aluguel["data_inicio"],
        "status": "pendente",
        "tipo": "diaria",
    }).execute()


def get_dashboard_stats(db: Client) -> dict:
    res = db.rpc("get_dashboard_stats").execute()
    return res.data if res.data else {}
