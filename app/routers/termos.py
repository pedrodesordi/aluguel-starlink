from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from supabase import Client

from app.database import get_db
from app.services.termo_service import registrar_aceite

router = APIRouter(tags=["termos"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/{token}")
def ver_termo(token: str, request: Request, db: Client = Depends(get_db)):
    res = db.table("termos_responsabilidade").select("*,alugueis(*,clientes(*),equipamentos(*))").eq("token", token).execute()
    if not res.data:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

    termo = res.data[0]
    aluguel = termo.get("alugueis", {})

    if termo["status"] == "aceito":
        return templates.TemplateResponse("termos/aceito.html", {
            "request": request, "termo": termo, "aluguel": aluguel,
        })
    if termo["status"] == "expirado":
        return templates.TemplateResponse("termos/aceite.html", {
            "request": request, "termo": termo, "aluguel": aluguel,
            "erro": "Este link expirou. Solicite um novo link ao responsável.",
        })

    return templates.TemplateResponse("termos/aceite.html", {
        "request": request, "termo": termo, "aluguel": aluguel,
    })


@router.post("/{token}/aceitar")
def aceitar_termo(token: str, request: Request, db: Client = Depends(get_db)):
    ip = request.client.host if request.client else "desconhecido"
    user_agent = request.headers.get("user-agent", "")
    try:
        registrar_aceite(token, ip, user_agent, db)
    except ValueError as e:
        res = db.table("termos_responsabilidade").select("*,alugueis(*,clientes(*),equipamentos(*))").eq("token", token).execute()
        termo = res.data[0] if res.data else {}
        return templates.TemplateResponse("termos/aceite.html", {
            "request": request, "termo": termo, "aluguel": termo.get("alugueis", {}),
            "erro": str(e),
        }, status_code=400)

    return RedirectResponse(f"/termos/{token}", status_code=303)


@router.get("/{token}/pdf")
def baixar_pdf(token: str, db: Client = Depends(get_db)):
    res = db.table("termos_responsabilidade").select("pdf_path,status").eq("token", token).execute()
    if not res.data or res.data[0]["status"] != "aceito" or not res.data[0]["pdf_path"]:
        return {"erro": "PDF não disponível"}
    return FileResponse(res.data[0]["pdf_path"], media_type="application/pdf", filename="termo_responsabilidade.pdf")
