from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, RedirectResponse
from app.templates_config import templates
from supabase import Client

from app.database import get_db
from app.services.termo_service import registrar_aceite

router = APIRouter(tags=["termos"])


def _calcular_valor_liquido(aluguel_id: str, db: Client) -> float:
    pags = db.table("pagamentos").select("valor,desconto").eq("aluguel_id", aluguel_id).neq("tipo", "multa").execute().data
    return sum(float(p["valor"]) - float(p.get("desconto") or 0) for p in pags)


@router.get("/{token}")
def ver_termo(token: str, request: Request, db: Client = Depends(get_db)):
    res = db.table("termos_responsabilidade").select("*,alugueis(*,clientes(*),equipamentos(*))").eq("token", token).execute()
    if not res.data:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

    termo = res.data[0]
    aluguel = termo.get("alugueis", {})
    valor_liquido = _calcular_valor_liquido(aluguel["id"], db) if aluguel.get("id") else 0

    if termo["status"] == "aceito":
        return templates.TemplateResponse("termos/aceito.html", {
            "request": request, "termo": termo, "aluguel": aluguel, "valor_liquido": valor_liquido,
        })
    if termo["status"] == "expirado":
        return templates.TemplateResponse("termos/aceite.html", {
            "request": request, "termo": termo, "aluguel": aluguel, "valor_liquido": valor_liquido,
            "erro": "Este link expirou. Solicite um novo link ao responsável.",
        })

    return templates.TemplateResponse("termos/aceite.html", {
        "request": request, "termo": termo, "aluguel": aluguel, "valor_liquido": valor_liquido,
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
        aluguel = termo.get("alugueis", {})
        valor_liquido = _calcular_valor_liquido(aluguel["id"], db) if aluguel.get("id") else 0
        return templates.TemplateResponse("termos/aceite.html", {
            "request": request, "termo": termo, "aluguel": aluguel, "valor_liquido": valor_liquido,
            "erro": str(e),
        }, status_code=400)

    return RedirectResponse(f"/termos/{token}", status_code=303)


@router.get("/{token}/pdf")
def baixar_pdf(token: str, db: Client = Depends(get_db)):
    res = db.table("termos_responsabilidade").select("pdf_path,status").eq("token", token).execute()
    if not res.data or res.data[0]["status"] != "aceito" or not res.data[0]["pdf_path"]:
        return {"erro": "PDF não disponível"}
    return FileResponse(res.data[0]["pdf_path"], media_type="application/pdf", filename="termo_responsabilidade.pdf")
