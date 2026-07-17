"""
Генератор заполненной декларации УСН (Титульный лист + Разд. 1.1 + Разд. 2.1.1).
Координаты полей откалиброваны по реальной, ранее принятой ФНС декларации.

Использование из app.py:
    from pdf_generator import generate_pdf, build_declaration_data
    data = build_declaration_data(personal_info, calc_result)
    generate_pdf(data, "/mnt/user-data/outputs/declaration.pdf")
"""
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader, PdfWriter
import json, io, os, sys

PAGE_W, PAGE_H = 595, 842
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TILE_DIR = os.path.join(BASE_DIR, "pdf_template")
FONT_PATH = os.path.join(BASE_DIR, "fonts", "DejaVuSansMono.ttf")

# Отношение pitch (шаг между клетками бланка) к размеру шрифта.
# Официальная норма ФНС — Courier New 16-18pt; 0.665 держит текст
# в этом диапазоне (~18.5pt при pitch ~12.3), а не ~20.5pt, как было при 0.6.
FONT_SIZE_RATIO = 0.665

# Встраиваем шрифт с поддержкой кириллицы прямо в PDF — иначе на компьютере,
# где нет подходящего системного шрифта для замены, вместо букв рисуются
# сплошные чёрные прямоугольники ("не найден символ").
FONT_NAME = "DejaVuSansMono"
pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))

with open(os.path.join(TILE_DIR, "tile_data.json")) as f:
    TILES = json.load(f)


def y(top):
    return PAGE_H - top


# (page_idx, align, x_ref, top, pitch, ncells)
FIELDS = {
    "inn":              (0, "left", 219.8, 10.3, 12.345, 12),
    "page_num":         (0, "left", 355.6, 30.0, 12.3, 3),
    "correction_num":   (0, "left", 158.3, 99.1, 12.3, 1),
    "period_code":      (0, "left", 343.2, 99.1, 9.35, 2),
    "year":             (0, "left", 515.9, 99.1, 12.3, 4),
    "tax_authority":    (0, "left", 227.3, 121.3, 12.3, 4),
    "location_code":    (0, "left", 528.1, 121.3, 12.35, 3),
    "fio_line1":        (0, "left", 71.9, 148.4, 12.35, 20),
    "fio_line2":        (0, "left", 71.9, 168.1, 12.35, 20),
    "fio_line3":        (0, "left", 71.9, 187.9, 12.35, 20),
    "phone":            (0, "left", 195.2, 279.1, 12.3, 15),
    "tax_object":       (0, "left", 170.5, 318.6, 12.3, 1),
    "pages_count":      (0, "left", 96.6, 456.7, 12.3, 2),
    "confirm_code":     (0, "left", 89.2, 503.5, 12.3, 1),

    "oktmo_010":        (1, "left", 404.9, 128.6, 12.31, 8),
    "line_100":         (1, "right", 555.2, 466.6, 12.32, 6),

    "flag_101":         (2, "left", 417.2, 106.4, 12.3, 1),
    "flag_102":         (2, "left", 417.2, 185.4, 12.3, 1),
    "income_110":       (2, "right", 555.2, 254.5, 12.32, 6),
    "income_111":       (2, "right", 555.2, 276.6, 12.32, 6),
    "income_112":       (2, "right", 555.2, 298.8, 12.32, 6),
    "income_113":       (2, "right", 555.2, 321.0, 12.32, 6),
    "rate_120":         (2, "left", 444.2, 360.5, 12.3, 2),
    "rate_121":         (2, "left", 444.2, 382.7, 12.3, 2),
    "rate_122":         (2, "left", 444.2, 404.9, 12.3, 2),
    "rate_123":         (2, "left", 444.2, 429.6, 12.3, 2),
    "tax_130":          (2, "right", 555.2, 496.2, 12.32, 6),
    "tax_131":          (2, "right", 555.2, 528.2, 12.32, 6),
    "tax_132":          (2, "right", 555.2, 584.9, 12.32, 6),
    "tax_133":          (2, "right", 555.2, 639.1, 12.32, 6),

    "deduction_140":    (3, "right", 555.2, 138.6, 12.32, 6),
    "deduction_141":    (3, "right", 555.2, 173.0, 12.32, 6),
    "deduction_142":    (3, "right", 555.2, 205.1, 12.32, 6),
    "deduction_143":    (3, "right", 555.2, 237.2, 12.32, 6),
}


def draw_field(c, key, text):
    page_idx, align, x_ref, top, pitch, ncells = FIELDS[key]
    fontsize = pitch / FONT_SIZE_RATIO
    c.setFont(FONT_NAME, fontsize)
    text = str(text)[:ncells]
    n = len(text)
    if align == "left":
        start_x = x_ref
    else:
        start_x = x_ref - (ncells - 1) * pitch + (ncells - n) * pitch
    for i, ch in enumerate(text):
        c.drawString(start_x + i * pitch, y(top) - fontsize * 0.75, ch)


def build_overlay(data: dict) -> dict:
    buffers = {i: io.BytesIO() for i in range(4)}
    canvases = {i: canvas.Canvas(buffers[i], pagesize=(PAGE_W, PAGE_H)) for i in range(4)}

    for pnum in range(4):
        c = canvases[pnum]
        fontsize = FIELDS["inn"][4] / FONT_SIZE_RATIO
        c.setFont(FONT_NAME, fontsize)
        inn_text = str(data.get("inn", ""))
        for i, ch in enumerate(inn_text[:12]):
            c.drawString(219.8 + i * 12.345, y(10.3) - fontsize * 0.75, ch)
        fontsize2 = 12.3 / FONT_SIZE_RATIO
        c.setFont(FONT_NAME, fontsize2)
        for i, ch in enumerate(f"{pnum+1:03d}"):
            c.drawString(355.6 + i * 12.3, y(30.0) - fontsize2 * 0.75, ch)

    for key, value in data.items():
        if key == "inn" or key not in FIELDS:
            continue
        page_idx = FIELDS[key][0]
        draw_field(canvases[page_idx], key, value)

    for i in range(4):
        canvases[i].save()
        buffers[i].seek(0)
    return buffers


def build_background(page_idx: int) -> io.BytesIO:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    for tile in TILES[str(page_idx)]:
        x0, y0_, x1, y1 = tile["rect"]
        img_path = os.path.join(TILE_DIR, tile["file"])
        c.drawImage(ImageReader(img_path), x0, PAGE_H - y1, width=x1 - x0, height=y1 - y0_)
    c.save()
    buf.seek(0)
    return buf


def generate_pdf(data: dict, output_path: str):
    overlays = build_overlay(data)
    writer = PdfWriter()
    for pnum in range(4):
        bg_reader = PdfReader(build_background(pnum))
        overlay_reader = PdfReader(overlays[pnum])
        page = bg_reader.pages[0]
        page.merge_page(overlay_reader.pages[0])
        writer.add_page(page)
    with open(output_path, "wb") as f:
        writer.write(f)


def build_declaration_data(personal: dict, calc_result: dict) -> dict:
    q = calc_result["quarters"]
    return {
        "inn": personal["inn"],
        "correction_num": personal.get("correction_num", "0"),
        "period_code": personal.get("period_code", "34"),
        "year": str(personal["year"]),
        "tax_authority": personal["tax_authority"],
        "location_code": personal.get("location_code", "120"),
        "fio_line1": personal.get("fio_line1", ""),
        "fio_line2": personal.get("fio_line2", ""),
        "fio_line3": personal.get("fio_line3", ""),
        "phone": personal.get("phone", ""),
        "tax_object": "1",
        "pages_count": "4",
        "confirm_code": "1",
        "oktmo_010": personal["oktmo"],
        "line_100": str(calc_result["total_tax_for_year"]),
        "flag_101": "1",
        "flag_102": "1" if personal.get("has_employees") else "2",
        "income_110": str(q[0]["cumulative_income"]),
        "income_111": str(q[1]["cumulative_income"]),
        "income_112": str(q[2]["cumulative_income"]),
        "income_113": str(q[3]["cumulative_income"]),
        "rate_120": str(int(personal["tax_rate"])),
        "rate_121": str(int(personal["tax_rate"])),
        "rate_122": str(int(personal["tax_rate"])),
        "rate_123": str(int(personal["tax_rate"])),
        "tax_130": str(q[0]["base_tax_cumulative"]),
        "tax_131": str(q[1]["base_tax_cumulative"]),
        "tax_132": str(q[2]["base_tax_cumulative"]),
        "tax_133": str(q[3]["base_tax_cumulative"]),
        "deduction_140": str(q[0]["deduction_cumulative"]),
        "deduction_141": str(q[1]["deduction_cumulative"]),
        "deduction_142": str(q[2]["deduction_cumulative"]),
        "deduction_143": str(q[3]["deduction_cumulative"]),
    }
