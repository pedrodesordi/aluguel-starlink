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
    flash = request.session.pop("flash", None)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "stats": stats,
        "alugueis_recentes": alugueis_recentes,
        "vencimentos": vencimentos,
        "flash": flash,
    })
