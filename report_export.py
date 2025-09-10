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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from urllib.parse import urlparse

# ----------------------------
# Универсальные хелперы
# ----------------------------

def _register_cyrillic_fonts():
    """Регистрирует кириллические шрифты для ReportLab"""
    try:
        # Пытаемся использовать системные шрифты Windows
        font_paths = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf", 
            "C:/Windows/Fonts/tahoma.ttf",
            "C:/Windows/Fonts/verdana.ttf"
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('CyrillicFont', font_path))
                    pdfmetrics.registerFont(TTFont('CyrillicFontBold', font_path))
                    return True
                except:
                    continue
        
        # Если системные шрифты не найдены, используем встроенные
        return False
    except:
        return False

# Регистрируем кириллические шрифты при импорте модуля
_cyrillic_fonts_available = _register_cyrillic_fonts()

def _clean_markdown(text: str) -> str:
    """Убирает markdown разметку из текста"""
    import re
    
    # Убираем заголовки (###, ####, ##, #)
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    
    # Убираем жирный текст (**text** или __text__)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    
    # Убираем курсив (*text* или _text_)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    
    # Убираем код (`code`)
    text = re.sub(r'`(.*?)`', r'\1', text)
    
    # Убираем ссылки [text](url)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # Убираем лишние пробелы и переносы строк
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    text = text.strip()
    
    return text

def _default_output_path(dir_: str | Path = "reports", prefix: str = "competitors_report") -> Path:
    Path(dir_).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    return Path(dir_) / f"{prefix}_{ts}.pdf"


def _styles():
    styles = getSampleStyleSheet()

    # Выбираем шрифт в зависимости от доступности кириллических шрифтов
    if _cyrillic_fonts_available:
        font_name = "CyrillicFont"
        font_bold = "CyrillicFontBold"
    else:
        # Fallback на шрифты, которые лучше поддерживают кириллицу
        font_name = "Times-Roman"
        font_bold = "Times-Bold"

    # Базовые
    h1 = ParagraphStyle(
        "H1",
        parent=styles["Heading1"],
        fontName=font_bold,
        fontSize=20,
        spaceAfter=10,
        textColor=colors.HexColor("#222222"),
    )
    h2 = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontName=font_bold,
        fontSize=14,
        textColor=colors.HexColor("#333333"),
        spaceBefore=8,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=10.5,
        leading=14,
    )
    small = ParagraphStyle(
        "Small",
        parent=styles["BodyText"],
        fontName=font_name,
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
    urls: Optional[List[str]] = None,
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
    
    # Вступление
    if urls and len(urls) >= 2:
        intro_text = f"""
        <b>Цель отчёта:</b> Провести стратегический анализ {len(urls)} конкурентов для выявления возможностей развития нашего бизнеса.
        
        <b>Проанализированные сайты:</b> {', '.join([urlparse(url).netloc for url in urls if urlparse(url).netloc])}
        
        <b>Методология:</b> Автоматический анализ с помощью AI-агентов, включающий извлечение данных, сравнительный анализ и формирование стратегических рекомендаций для нашего бизнеса.
        
        <b>Фокус анализа:</b> Определить, что позаимствовать у сильных конкурентов, какие слабые стороны конкурентов дают нам преимущество, и как использовать эти знания для обгона.
        """
        flow.append(Paragraph(intro_text, body))
        flow.append(Spacer(1, 12))

    # Секции
    for sec_title, sec_text in sections:
        if sec_title:
            flow.append(Paragraph(sec_title, h2))
        flow += _paragraphs_from_text(sec_text or "", body)
        flow.append(Spacer(1, 6))

    # Создаем таблицу сравнения конкурентов (если есть URL)
    if urls and len(urls) >= 2:
        comparison_table = _create_competitor_comparison_table(
            "\n".join([text for _, text in sections]), urls
        )
        if comparison_table:
            if not table_blocks:
                table_blocks = []
            table_blocks.insert(0, comparison_table)  # Добавляем в начало

    # Таблицы (если есть)
    if table_blocks:
        for tbl_title, data in table_blocks:
            flow.append(Spacer(1, 6))
            if tbl_title:
                flow.append(Paragraph(tbl_title, h2))
            if data and len(data) > 0:
                t = Table(data, repeatRows=1)
                # Выбираем шрифт для таблицы
                table_font = "CyrillicFont" if _cyrillic_fonts_available else "Times-Roman"
                
                t.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F2F2")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111111")),
                        ("FONTNAME", (0, 0), (-1, -1), table_font),
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


def _create_competitor_comparison_table(report_text: str, urls: List[str]) -> Optional[Tuple[str, List[List[str]]]]:
    """
    Создает таблицу сравнения конкурентов на основе отчета и URL.
    Возвращает кортеж (заголовок, данные таблицы) или None если данных недостаточно.
    """
    if not report_text or not urls:
        return None
    
    # Извлекаем домены из URL
    from urllib.parse import urlparse
    domains = []
    for url in urls:
        try:
            domain = urlparse(url).netloc
            if domain:
                domains.append(domain)
        except:
            continue
    
    if len(domains) < 2:
        return None
    
    # Простой парсинг данных из отчета
    text_lower = report_text.lower()
    
    # Заголовки таблицы
    headers = ["Конкурент", "Сильные стороны", "Слабые стороны", "Возможности для нас"]
    
    # Данные таблицы
    table_data = [headers]
    
    for domain in domains:
        row = [domain]
        
        # Ищем упоминания домена в тексте
        domain_section = ""
        lines = report_text.split('\n')
        in_domain_section = False
        
        for line in lines:
            if domain.lower() in line.lower():
                in_domain_section = True
                domain_section += line + " "
            elif in_domain_section and line.strip() and not line.startswith(' '):
                # Если начинается новый раздел, прекращаем сбор
                break
        
        # Извлекаем данные для каждой колонки
        strengths = _extract_keywords(domain_section, ['сильные', 'преимущества', 'плюсы', 'хорошо', 'эффективно'])
        weaknesses = _extract_keywords(domain_section, ['слабые', 'недостатки', 'минусы', 'проблемы', 'плохо'])
        opportunities = _extract_keywords(domain_section, ['возможности', 'позаимствовать', 'обойти', 'выделиться', 'уникально'])
        
        row.extend([strengths, weaknesses, opportunities])
        table_data.append(row)
    
    return ("Сравнительная таблица конкурентов", table_data)

def _extract_keywords(text: str, keywords: List[str]) -> str:
    """Извлекает релевантные фразы из текста по ключевым словам."""
    if not text:
        return "Данные не найдены"
    
    sentences = text.split('.')
    relevant_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if any(keyword in sentence.lower() for keyword in keywords):
            # Ограничиваем длину предложения
            if len(sentence) > 100:
                sentence = sentence[:100] + "..."
            relevant_sentences.append(sentence)
    
    if relevant_sentences:
        return ". ".join(relevant_sentences[:2])  # Максимум 2 предложения
    else:
        return "Данные не найдены"

def make_sections_from_result(raw_result: str) -> List[Tuple[str, str]]:
    """
    Если у тебя один длинный текст от CrewAI — разбиваем на секции по простым «якорям».
    Работает tolerant-режимом: если якорей нет, вернёт одну секцию «Отчёт».
    """
    # Очищаем markdown разметку
    cleaned_result = _clean_markdown(raw_result or "")
    
    # Убираем дубли и повторяющиеся блоки
    cleaned_result = _remove_duplicates(cleaned_result)
    
    anchors = [
        ("Краткая сводка", ["краткая сводка", "сводка", "резюме"]),
        ("Анализ конкурентов", ["обзор", "корпус", "сырые данные", "анализ сайтов", "извлечённые факты"]),
        ("Сравнительный анализ", ["сильные", "слабые", "отличия", "тренды", "сравнение", "пробелы"]),
        ("Стратегические рекомендации", ["позаимствовать", "обойти", "возможности", "план действий", "рекомендации"]),
    ]

    lower = cleaned_result.lower()
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
                    chunk = cleaned_result[last_idx:idx].strip()
                    if chunk and len(chunk) > 50:  # Игнорируем слишком короткие блоки
                        parts.append((title if not found_any else "Продолжение", chunk))
                        found_any = True
                last_idx = idx
                break

    # хвост
    tail = cleaned_result[last_idx:].strip()
    if tail and len(tail) > 50:
        parts.append(("Заключение", tail))

    if not parts:
        parts = [("Отчёт", cleaned_result)]
    return parts

def _remove_duplicates(text: str) -> str:
    """Убирает дублирующиеся блоки текста."""
    if not text:
        return text
    
    lines = text.split('\n')
    seen_blocks = set()
    unique_lines = []
    
    current_block = ""
    for line in lines:
        line = line.strip()
        if not line:
            if current_block and current_block not in seen_blocks:
                seen_blocks.add(current_block)
                unique_lines.append(current_block)
            current_block = ""
        else:
            current_block += line + " "
    
    # Добавляем последний блок
    if current_block and current_block not in seen_blocks:
        unique_lines.append(current_block)
    
    return '\n\n'.join(unique_lines)
