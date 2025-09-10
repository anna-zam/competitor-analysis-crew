# report_export.py
# Генерация PDF-отчёта по анализу конкурентов (ReportLab)

from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    Image,
)

# ----------------------------
# Универсальные хелперы
# ----------------------------

def _default_output_path(dir_: str | Path = "reports", prefix: str = "competitors_report") -> Path:
    Path(dir_).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    return Path(dir_) / f"{prefix}_{ts}.pdf"


def _styles():
    styles = getSampleStyleSheet()

    # Базовые
    h1 = ParagraphStyle(
        "H1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        spaceAfter=10,
        textColor=colors.HexColor("#222222"),
    )
    h2 = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=colors.HexColor("#333333"),
        spaceBefore=8,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
    )
    small = ParagraphStyle(
        "Small",
        parent=styles["BodyText"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        textColor=colors.HexColor("#666666"),
    )
    return h1, h2, body, small


def _paragraphs_from_text(text: str, style: ParagraphStyle, chunk: int = 1800) -> List[Paragraph]:
    """
    Безопасно режем длинный текст на блоки, чтобы ReportLab не упал.
    """
    text = text.strip() if text else ""
    if not text:
        return []
    pieces = []
    for i in range(0, len(text), chunk):
        pieces.append(Paragraph(text[i:i+chunk].replace("\n", "<br/>"), style))
        pieces.append(Spacer(1, 4))
    return pieces


# ----------------------------
# Публичные функции
# ----------------------------

def save_pdf_report(
    title: str,
    sections: List[Tuple[str, str]],
    table_blocks: Optional[List[Tuple[str, List[List[str]]]]] = None,
    output_path: Optional[str | Path] = None,
    images: Optional[List[str]] = None,
) -> Path:
    """
    Генерирует PDF.
    :param title: Заголовок отчёта
    :param sections: Список секций вида (заголовок, текст)
    :param table_blocks: Необязательные таблицы [(заголовок, данные-2D)]
    :param output_path: Путь до .pdf (если None — создадим автоматически в ./reports)
    :param images: Список путей к изображениям для вставки в PDF
    :return: Path до PDF
    """
    h1, h2, body, small = _styles()
    pdf_path = Path(output_path) if output_path else _default_output_path()

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=14 * mm,
        title=title,
    )

    flow = []

    # Титул
    flow.append(Paragraph(title, h1))
    flow.append(Paragraph(datetime.now().strftime("Отчёт сформирован: %d.%m.%Y %H:%M"), small))
    flow.append(Spacer(1, 10))

    # Секции
    for sec_title, sec_text in sections:
        if sec_title:
            flow.append(Paragraph(sec_title, h2))
        flow += _paragraphs_from_text(sec_text or "", body)
        flow.append(Spacer(1, 6))

    # Таблицы (если есть)
    if table_blocks:
        for tbl_title, data in table_blocks:
            flow.append(Spacer(1, 6))
            if tbl_title:
                flow.append(Paragraph(tbl_title, h2))
            if data and len(data) > 0:
                t = Table(data, repeatRows=1)
                t.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F2F2")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111111")),
                        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FBFBFB")]),
                    ])
                )
                flow.append(t)
            flow.append(Spacer(1, 8))

    # Вставка изображений
    if images:
        flow.append(Spacer(1, 12))
        flow.append(Paragraph("Визуализация", h2))
        flow.append(Spacer(1, 6))
        
        for img_path in images:
            try:
                # Проверяем существование файла
                img_file = Path(img_path)
                if not img_file.exists():
                    print(f"Предупреждение: файл изображения не найден: {img_path}")
                    continue
                
                # Создаем объект изображения с авто-масштабированием
                img = Image(str(img_file))
                
                # Авто-масштабирование по ширине (максимум 170mm)
                max_width = 170 * mm
                if img.drawWidth > max_width:
                    ratio = max_width / img.drawWidth
                    img.drawWidth = max_width
                    img.drawHeight = img.drawHeight * ratio
                
                # Добавляем заголовок изображения
                img_name = img_file.stem.replace("_", " ").title()
                flow.append(Paragraph(f"<b>{img_name}</b>", body))
                flow.append(Spacer(1, 4))
                
                # Добавляем изображение
                flow.append(img)
                flow.append(Spacer(1, 8))
                
            except Exception as e:
                print(f"Ошибка при добавлении изображения {img_path}: {e}")
                # Добавляем текстовое описание вместо изображения
                flow.append(Paragraph(f"<i>Изображение недоступно: {Path(img_path).name}</i>", small))
                flow.append(Spacer(1, 8))

    # Разделитель + подпись
    flow.append(PageBreak())

    flow.append(Paragraph("© LeadByIT — Автономные агенты и автоматизация процессов", small))

    doc.build(flow)
    return pdf_path


def make_sections_from_result(raw_result: str) -> List[Tuple[str, str]]:
    """
    Если у тебя один длинный текст от CrewAI — разбиваем на секции по простым «якорям».
    Работает tolerant-режимом: если якорей нет, вернёт одну секцию «Отчёт».
    """
    anchors = [
        ("Обзор конкурентов", ["обзор", "корпус", "сырые данные"]),
        ("Извлечённые факты", ["утп", "позиционирование", "сегменты", "услуги", "cta", "seo"]),
        ("Сравнительный анализ", ["сильные", "слабые", "отличия", "тренды"]),
        ("Рекомендации и план", ["рекомендации", "план", "шаги", "недели"]),
    ]

    lower = (raw_result or "").lower()
    parts: List[Tuple[str, str]] = []

    # очень грубо: если находим ключи — режем, иначе одна секция
    last_idx = 0
    found_any = False
    for title, keys in anchors:
        for k in keys:
            idx = lower.find(k)
            if idx != -1:
                if idx > last_idx:
                    # всё до текущего якоря отправим под названием предыдущей секции (или «Отчёт»)
                    chunk = raw_result[last_idx:idx].strip()
                    if chunk:
                        parts.append((title if not found_any else "Продолжение", chunk))
                        found_any = True
                last_idx = idx
                break

    # хвост
    tail = raw_result[last_idx:].strip()
    if tail:
        parts.append(("Отчёт", tail))

    if not parts:
        parts = [("Отчёт", raw_result or "")]
    return parts
