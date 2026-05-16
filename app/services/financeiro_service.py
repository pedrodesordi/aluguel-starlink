import calendar
from datetime import date, timedelta

from supabase import Client


def _proximo_mes(d: date) -> date:
    if d.month == 12:
        return d.replace(year=d.year + 1, month=1)
    novo_mes = d.month + 1
    ultimo_dia = calendar.monthrange(d.year, novo_mes)[1]
    return d.replace(month=novo_mes, day=min(d.day, ultimo_dia))


def gerar_parcelas_mensais(aluguel: dict, db: Client, desconto: float = 0) -> None:
    inicio = date.fromisoformat(aluguel["data_inicio"])
    fim = date.fromisoformat(aluguel["data_fim_prevista"])
    parcelas = []
    cursor = inicio
    i = 1
    while cursor <= fim:
        proximo = _proximo_mes(cursor)
        vencimento = min(proximo - timedelta(days=1), fim)
        parcela: dict = {
            "aluguel_id": aluguel["id"],
            "descricao": f"Mensalidade {cursor.strftime('%m/%Y')} - Parcela {i}",
            "valor": float(aluguel["valor_contratado"]),
            "data_vencimento": str(vencimento),
            "status": "pendente",
            "tipo": "mensalidade",
        }
        if i == 1 and desconto > 0:
            parcela["desconto"] = desconto
        parcelas.append(parcela)
        cursor = proximo
        i += 1
    if parcelas:
        db.table("pagamentos").insert(parcelas).execute()


def gerar_pagamento_diaria(aluguel: dict, db: Client, desconto: float = 0) -> None:
    pagamento: dict = {
        "aluguel_id": aluguel["id"],
        "descricao": f"Aluguel diário — {aluguel['data_inicio']} a {aluguel['data_fim_prevista']}",
        "valor": float(aluguel["valor_total_previsto"]),
        "data_vencimento": aluguel["data_fim_prevista"],
        "status": "pendente",
        "tipo": "diaria",
    }
    if desconto > 0:
        pagamento["desconto"] = desconto
    db.table("pagamentos").insert(pagamento).execute()


def get_dashboard_stats(db: Client) -> dict:
    res = db.rpc("get_dashboard_stats").execute()
    return res.data if res.data else {}


def get_vencimentos_proximos(db: Client, dias: int = 10) -> list:
    hoje = date.today()
    dia_hoje = hoje.day

    res = (
        db.table("equipamentos")
        .select("id,modelo,numero_serie,numero_starlink,tipo_plano,vencimento_mensalidade,status")
        .not_.is_("vencimento_mensalidade", "null")
        .neq("status", "baixado")
        .execute()
    )

    resultado = []
    for e in res.data:
        dia_venc = e["vencimento_mensalidade"]
        if dia_venc >= dia_hoje:
            dias_faltam = dia_venc - dia_hoje
        else:
            ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
            dias_faltam = (ultimo_dia - dia_hoje) + dia_venc

        if dias_faltam <= dias:
            e["dias_faltam"] = dias_faltam
            resultado.append(e)

    return sorted(resultado, key=lambda x: x["dias_faltam"])
