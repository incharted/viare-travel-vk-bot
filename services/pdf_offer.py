from __future__ import annotations

from datetime import datetime
from pathlib import Path


def _load_reportlab():
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas
    except Exception as err:  # noqa: BLE001
        raise RuntimeError("PDF library is not installed. Add reportlab dependency.") from err
    return A4, canvas, pdfmetrics, TTFont


def _select_font(pdfmetrics, TTFont) -> tuple[str, bool]:
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    ]
    for path in candidates:
        if path.exists():
            font_name = "OfferFont"
            try:
                pdfmetrics.registerFont(TTFont(font_name, str(path)))
                return font_name, True
            except Exception:
                continue
    return "Helvetica", False


def _normalize_text(value: str, unicode_supported: bool) -> str:
    text = value.strip()
    if unicode_supported:
        return text
    return text.encode("ascii", errors="ignore").decode("ascii")


def _currency(value: int | None) -> str:
    if value is None:
        return "-"
    return f"{value:,} RUB".replace(",", " ")


def build_offer_pdf(request_data: dict, tours: list[dict], output_dir: Path | None = None) -> Path:
    A4, canvas, pdfmetrics, TTFont = _load_reportlab()
    output_base = output_dir or Path("./data/exports")
    output_base.mkdir(parents=True, exist_ok=True)

    filename = f"offer_request_{request_data['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    path = output_base / filename

    page_width, page_height = A4
    pdf = canvas.Canvas(str(path), pagesize=A4)
    font_name, unicode_supported = _select_font(pdfmetrics, TTFont)

    def write_line(text: str, y: float, size: int = 11) -> float:
        pdf.setFont(font_name, size)
        pdf.drawString(42, y, _normalize_text(text, unicode_supported))
        return y - (size + 4)

    y = page_height - 52
    y = write_line("VIARE Travel - Commercial Offer", y, size=16)
    y = write_line(f"Request ID: {request_data['id']}", y)
    y = write_line(f"Client VK: {request_data.get('vk_id', '-')}", y)
    y = write_line(f"Destination: {request_data.get('destination') or request_data.get('country') or '-'}", y)
    y = write_line(f"Dates: {request_data.get('start_date', '-')} - {request_data.get('end_date', '-')}", y)
    y = write_line(f"Travelers: {request_data.get('travelers', '-')}", y)
    y = write_line(f"Budget: {_currency(request_data.get('budget'))}", y)
    y = write_line(f"Rest type: {request_data.get('rest_type', '-')}", y)
    y -= 6
    y = write_line("Selected tour options:", y, size=12)

    if not tours:
        y = write_line("No prepared options. Manager manual selection required.", y)
    else:
        for index, tour in enumerate(tours[:3], start=1):
            total = int(tour.get("price_per_person", 0)) * int(request_data.get("travelers") or 1)
            destination = tour.get("destination") or tour.get("country") or "-"
            y = write_line(f"{index}. {tour.get('name', 'Tour option')}", y, size=12)
            y = write_line(f"   Destination: {destination}", y)
            y = write_line(f"   Rest type: {tour.get('rest_type', '-')}", y)
            y = write_line(f"   Price per person: {_currency(int(tour.get('price_per_person', 0)))}", y)
            y = write_line(f"   Total for group: {_currency(total)}", y)
            desc = str(tour.get("description") or "")
            if desc:
                y = write_line(f"   Note: {desc[:140]}", y)
            y -= 4
            if y < 110:
                pdf.showPage()
                y = page_height - 52

    y = max(y - 10, 75)
    y = write_line("Contact manager in VK community messages to confirm booking.", y)
    y = write_line("Generated automatically by VIARE Travel bot.", y)

    pdf.showPage()
    pdf.save()
    return path
