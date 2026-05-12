import asyncio
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse

from app.auth import NaoAutenticado, SemPermissao
from app.config import get_settings
from app.database import get_db
from app.routers import auth, dashboard, clientes, equipamentos, alugueis, financeiro, termos, configuracoes, admin, reservas
from app.templates_config import templates


async def daily_status_update():
    while True:
        await asyncio.sleep(3600)
        try:
            db = get_db()
            hoje = str(date.today())
            db.table("alugueis").update({"status": "atrasado"}).eq("status", "ativo").lt("data_fim_prevista", hoje).execute()
            db.table("pagamentos").update({"status": "vencido"}).eq("status", "pendente").lt("data_vencimento", hoje).execute()
            db.rpc("sync_status_equipamentos_hoje").execute()
        except Exception as e:
            print(f"[status-update] erro: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(daily_status_update())
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(clientes.router, prefix="/clientes")
app.include_router(equipamentos.router, prefix="/equipamentos")
app.include_router(alugueis.router, prefix="/alugueis")
app.include_router(financeiro.router, prefix="/financeiro")
app.include_router(termos.router, prefix="/termos")
app.include_router(configuracoes.router, prefix="/configuracoes")
app.include_router(admin.router, prefix="/admin")
app.include_router(reservas.router)


@app.exception_handler(NaoAutenticado)
async def handle_nao_autenticado(request: Request, exc: NaoAutenticado):
    return RedirectResponse("/login", status_code=302)


@app.exception_handler(SemPermissao)
async def handle_sem_permissao(request: Request, exc: SemPermissao):
    return templates.TemplateResponse("403.html", {"request": request}, status_code=403)
