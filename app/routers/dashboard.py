import json

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

    flash = request.session.pop("flash", None)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "stats": stats,
        "alugueis_recentes": alugueis_recentes,
        "vencimentos": vencimentos,
        "flash": flash,
        "eventos_json": json.dumps(eventos),
    })
