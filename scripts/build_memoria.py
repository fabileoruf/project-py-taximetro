"""Genera la memoria PDF desde docs/memoria.md con ReportLab."""

from html import escape
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
INK = colors.HexColor("#242821")
MUTED = colors.HexColor("#70776a")
YELLOW = colors.HexColor("#f5cd47")
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverTitle", fontName="Helvetica-Bold", fontSize=51, leading=60, textColor=INK, spaceAfter=18))
styles.add(ParagraphStyle(name="Section", fontName="Helvetica-Bold", fontSize=21, leading=27, textColor=INK, spaceBefore=5, spaceAfter=16))
styles.add(ParagraphStyle(name="Subsection", fontName="Helvetica-Bold", fontSize=12, leading=17, textColor=INK, spaceBefore=14, spaceAfter=8))
styles.add(ParagraphStyle(name="Copy", fontName="Helvetica", fontSize=10, leading=15, textColor=INK, spaceAfter=10))
styles.add(ParagraphStyle(name="Cell", fontName="Helvetica", fontSize=9, leading=12, textColor=INK))
styles.add(ParagraphStyle(name="Caption", fontName="Helvetica", fontSize=8, leading=11, textColor=MUTED, spaceAfter=10))


def markup(text):
    text = escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r'<font name="Courier" size="9">\1</font>', text)
    text = re.sub(r"(https?://[^\s<]+)", r'<link href="\1" color="#416539">\1</link>', text)
    return text


def decorate(canvas, doc):
    width, height = A4
    canvas.saveState()
    canvas.setFillColor(colors.white)
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(48, height - 33, "taxitech.")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(width - 48, height - 33, "MEMORIA DEL PROYECTO / PYTHON")
    canvas.setStrokeColor(colors.HexColor("#e3e6dd"))
    canvas.line(48, height - 45, width - 48, height - 45)
    if doc.page == 1:
        canvas.setFillColor(YELLOW)
        canvas.rect(0, 0, width, 130, fill=1, stroke=0)
        canvas.setFillColor(INK)
        canvas.setFont("Helvetica-Bold", 18)
        canvas.drawString(48, 85, "Cada segundo cuenta.")
        canvas.setFont("Helvetica", 10)
        canvas.drawString(48, 62, "01 Terminal   /   02 Persistencia   /   03 Interfaz   /   04 Aplicación")
    else:
        canvas.setFont("Helvetica", 8)
        canvas.drawString(48, 29, "Fabiana Leonardo · Factoría F5")
        canvas.drawRightString(width - 48, 29, f"{doc.page:02d}")
    canvas.restoreState()


def main():
    story = []
    lines = (DOCS / "memoria.md").read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        index += 1
        if not line:
            continue
        if line == "---":
            story.append(PageBreak())
        elif line.startswith("# "):
            story.append(Spacer(1, 20))
            story.append(Paragraph(markup(line[2:]), styles["CoverTitle"]))
        elif line.startswith("## "):
            story.append(Paragraph(markup(line[3:]), styles["Section"]))
        elif line.startswith("### "):
            story.append(Paragraph(markup(line[4:]), styles["Subsection"]))
        elif line.startswith("!["):
            match = re.match(r"!\[(.*?)\]\((.*?)\)", line)
            graphic = Image(str(DOCS / match.group(2)))
            scale = min(490 / graphic.imageWidth, 460 / graphic.imageHeight)
            graphic.drawWidth = graphic.imageWidth * scale
            graphic.drawHeight = graphic.imageHeight * scale
            story.extend([graphic, Spacer(1, 8), Paragraph(markup(match.group(1)), styles["Caption"])])
        elif line.startswith("|"):
            rows = [line]
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(lines[index].strip())
                index += 1
            cells = []
            for row in rows:
                values = [part.strip() for part in row.strip("|").split("|")]
                if all(re.fullmatch(r"[-: ]+", value) for value in values):
                    continue
                cells.append([Paragraph(markup(value), styles["Cell"]) for value in values])
            table = Table(cells, colWidths=[180, 310], hAlign="LEFT", repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeefe5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("LINEBELOW", (0, 0), (-1, -1), .4, colors.HexColor("#e3e6dd")),
            ]))
            story.extend([table, Spacer(1, 14)])
        elif line.startswith("- "):
            story.append(Paragraph(markup(line[2:]), styles["Copy"], bulletText="•"))
        else:
            story.append(Paragraph(markup(line), styles["Copy"]))
    target = DOCS / "memoria-taximetro.pdf"
    doc = SimpleDocTemplate(str(target), pagesize=A4, rightMargin=48, leftMargin=48,
                            topMargin=67, bottomMargin=53, title="TaxiTech — Memoria técnica",
                            author="Fabiana Leonardo", subject="Taxímetro digital en Python, cuatro fases")
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    print(target)


if __name__ == "__main__":
    main()
