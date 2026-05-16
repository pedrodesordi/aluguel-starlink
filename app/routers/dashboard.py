import json
from datetime import date

from fastapi import APIRouter, Depends, Request
from app.templates_config import templates
from supabase import Client

from app.auth import get_current_user
from app.database import get_db
from app.services.financeiro_service import get_dashboard_stats, get_vencimentos_proximos

router = APIRouter(tags=["dashboard"])


@router.get("/")
def dashboard(request: Request, user: dict = Depends(get_current_user), db: Client = Depends(get_db)):
    stats = get_dashboard_stats(db)
    vencimentos = get_vencimentos_proximos(db, dias=10)
    alugueis_recentes = (
        db.table("alugueis")
        .select("id,status,data_inicio,data_fim_prevista,clientes(nome),equipamentos(modelo,numero_serie)")
        .in_("status", ["ativo", "atrasado"])
        .order("criado_em", desc=True)
        .limit(8)
        .execute()
        .data
    )

    # Eventos do calendário
    eventos = []
    for a in alugueis_recentes:
        eventos.append({
            "title": a["clientes"]["nome"] if a.get("clientes") else "—",
            "start": str(a["data_inicio"]),
            "end": str(a["data_fim_prevista"]),
            "url": f"/alugueis/{a['id']}",
            "color": "#dc3545" if a["status"] == "atrasado" else "#0d6efd",
        })

    reservas_confirmadas = (
        db.table("reservas")
        .select("nome_cliente,data_inicio,data_fim_prevista,id,aluguel_id")
        .eq("status", "confirmada")
        .not_.is_("data_inicio", "null")
        .execute()
        .data
    )
    for r in reservas_confirmadas:
        if r.get("aluguel_id"):
            continue  # já aparece como aluguel
        eventos.append({
            "title": f"[Reserva] {r['nome_cliente'] or ''}",
            "start": str(r["data_inicio"]),
            "end": str(r["data_fim_prevista"]),
            "color": "#198754",
        })

    # Gráfico financeiro — de abril/2026 até o mês atual
    hoje = date.today()
    inicio_grafico = date(2026, 4, 1)
    meses, labels = [], []
    ano, mes = inicio_grafico.year, inicio_grafico.month
    while (ano, mes) <= (hoje.year, hoje.month):
        meses.append(f"{ano}-{mes:02d}")
        labels.append(date(ano, mes, 1).strftime("%b/%y"))
        mes += 1
        if mes > 12:
            mes = 1
            ano += 1

    pags_pagos = (
        db.table("pagamentos").select("valor,desconto,data_vencimento")
        .eq("status", "pago").gte("data_vencimento", meses[0] + "-01").execute().data
    )
    receita_por_mes: dict[str, float] = {m: 0.0 for m in meses}
    for p in pags_pagos:
        m = (p.get("data_vencimento") or "")[:7]
        if m in receita_por_mes:
            receita_por_mes[m] += float(p["valor"]) - float(p.get("desconto") or 0)

    despesa_mensal = sum(
        float(e.get("custo_mensalidade") or 0)
        for e in db.table("equipamentos").select("custo_mensalidade").execute().data
    )

    grafico = {
        "labels": labels,
        "receita": [round(receita_por_mes[m], 2) for m in meses],
        "despesa": [round(despesa_mensal, 2)] * 6,
        "lucro": [round(receita_por_mes[m] - despesa_mensal, 2) for m in meses],
    }

    lucro_mes = grafico["lucro"][-1]

    flash = request.session.pop("flash", None)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "stats": stats,
        "alugueis_recentes": alugueis_recentes,
        "vencimentos": vencimentos,
        "flash": flash,
        "eventos_json": json.dumps(eventos),
        "grafico": grafico,
        "lucro_mes": lucro_mes,
    })
