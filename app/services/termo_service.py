from __future__ import annotations
import os
from datetime import datetime, timezone

from app.templates_config import templates
from supabase import Client



def registrar_aceite(token: str, ip: str, user_agent: str, db: Client) -> dict:
    res = db.table("termos_responsabilidade").select("*").eq("token", token).execute()
    if not res.data:
        raise ValueError("Termo não encontrado")
    termo = res.data[0]

    if termo["status"] != "pendente":
        raise ValueError("Este termo já foi processado")

    agora = datetime.now(timezone.utc)
    if agora.isoformat() > termo["expira_em"]:
        db.table("termos_responsabilidade").update({"status": "expirado"}).eq("token", token).execute()
        raise ValueError("Link expirado")

    db.table("termos_responsabilidade").update({
        "status": "aceito",
        "ip_aceite": ip,
        "user_agent": user_agent,
        "aceito_em": agora.isoformat(),
    }).eq("token", token).execute()

    aluguel_res = db.table("alugueis").select("*, clientes(*), equipamentos(*)").eq("id", termo["aluguel_id"]).execute()
    if aluguel_res.data:
        aluguel = aluguel_res.data[0]
        try:
            pags = db.table("pagamentos").select("valor,desconto").eq("aluguel_id", aluguel["id"]).neq("tipo", "multa").execute().data
            valor_liquido = sum(float(p["valor"]) - float(p.get("desconto") or 0) for p in pags)
            pdf_path = _gerar_pdf(aluguel, termo, ip, agora, valor_liquido)
            db.table("termos_responsabilidade").update({"pdf_path": pdf_path}).eq("token", token).execute()
            termo["pdf_path"] = pdf_path
        except Exception as e:
            print(f"[termo] Falha ao gerar PDF: {e}")

    termo["status"] = "aceito"
    return termo


def _gerar_pdf(aluguel: dict, termo: dict, ip: str, aceito_em: datetime, valor_liquido: float = 0) -> str:
    try:
        from weasyprint import HTML
    except OSError as e:
        raise RuntimeError(f"WeasyPrint não disponível: {e}") from e

    os.makedirs("static/termos", exist_ok=True)
    pdf_path = f"static/termos/{termo['token']}.pdf"

    html_content = templates.get_template("termos/template_termo.html").render({
        "aluguel": aluguel,
        "cliente": aluguel.get("clientes", {}),
        "equipamento": aluguel.get("equipamentos", {}),
        "termo": termo,
        "ip_aceite": ip,
        "aceito_em": aceito_em.strftime("%d/%m/%Y %H:%M:%S UTC"),
        "valor_liquido": valor_liquido,
    })

    HTML(string=html_content).write_pdf(pdf_path)
    return pdf_path
