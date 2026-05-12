from datetime import date
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")


def _format_brl(value) -> str:
    if value is None:
        return "R$ 0,00"
    return f"R$ {float(value):_.2f}".replace(".", ",").replace("_", ".")


def _format_date_br(value) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value[:10])
        except ValueError:
            return value
    return value.strftime("%d/%m/%Y")


templates.env.filters["brl"] = _format_brl
templates.env.filters["data_br"] = _format_date_br
