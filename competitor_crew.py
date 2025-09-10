# competitor_crew.py
# «Агент для анализа конкурентов»
# Требует: crewai, requests, beautifulsoup4, python-dotenv

import os
import re
import time
from urllib.parse import urlparse
from report_export import save_pdf_report, make_sections_from_result
from crewai.llm import LLM

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process

load_dotenv()
# если используешь LLM через CrewAI – положи ключи в .env
# os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
llm = LLM(
    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
    temperature=0.2,      # сдержаннее, меньше "воды"
    max_tokens=2000        # при необходимости увеличь
)
# -----------------------
# Утилиты (простые)
# -----------------------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0 Safari/537.36"
}

def fetch_html(url: str, timeout: int = 15) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        return f"__ERROR_FETCH__ {url}: {e}"

def extract_text(html: str) -> str:
    if html.startswith("__ERROR_FETCH__"):
        return html
    soup = BeautifulSoup(html, "html.parser")
    # Удаляем скрипты/стили
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    # мини-нормализация
    text = re.sub(r"\s+", " ", text).strip()
    return text[:60_000]  # ограничим объём

def domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc
    except:
        return url

# -----------------------
# Агенты
# -----------------------

reader = Agent(
    role="Competitive Research Crawler",
    goal=("Собрать контент конкурентов: скачать HTML по списку ссылок, "
          "выделить основной текст (без скриптов) и подготовить сырые данные."),
    backstory=(
        "Этот агент умеет аккуратно забирать страницы конкурентов, "
        "чтобы их потом разобрал аналитик. Он старается не падать при ошибках, "
        "помечая проблемные URL."
    ),
    tools=[],  # в уроке tools не использовали
    verbose=True,
    llm=llm,
)

extractor = Agent(
    role="Value Proposition Extractor",
    goal=("Извлечь из сырых текстов ключевую информацию: оффер/УТП, "
          "целевые сегменты, список услуг/товаров, ценовые сигналы, "
          "триггеры доверия (кейсы, отзывы, сертификаты), CTA."),
    backstory=(
        "Этот агент читает очищенный текст и вынимает факты. "
        "Результат — структурированный конспект по каждому конкуренту."
    ),
    tools=[],
    verbose=True,
    llm=llm,
)

analyst = Agent(
    role="Competitor Analyst",
    goal=("Сравнить конкурентов между собой: сильные/слабые стороны, "
          "позиционирование, SEO-сигналы (заголовки H1/Title из текста), "
          "контент-стратегия, воронка, офферы."),
    backstory=(
        "Этот агент делает сравнительный анализ и сводит находки в таблицу-подсказку, "
        "а также формулирует практические выводы."
    ),
    tools=[],
    verbose=True,
    llm=llm,
)

strategist = Agent(
    role="Strategic Advisor",
    goal=("Проанализировать конкурентов и сформировать стратегические рекомендации ДЛЯ НАШЕГО БИЗНЕСА: "
          "что позаимствовать у сильных конкурентов, какие слабые стороны конкурентов дают нам преимущество, "
          "какие уникальные возможности мы можем использовать для обгона."),
    backstory=(
        "Этот агент думает стратегически о том, как использовать анализ конкурентов в нашу пользу. "
        "Он не дает советы конкурентам, а формирует план действий для нашего бизнеса."
    ),
    tools=[],
    verbose=True,
    llm=llm,
)

# -----------------------
# Задачи (Tasks)
# -----------------------

# 1) Сбор сырых данных
task1 = Task(
    description=(
        "Получить HTML-конент по списку ссылок конкурентов и подготовить сырой корпус для анализа.\n"
        "Вход: список URL через запятую в переменной INPUT_URLS.\n"
        "Требуется: для каждого URL вернуть блок с полями:\n"
        "- url\n"
        "- domain\n"
        "- excerpt (первые 800–1200 символов очищенного текста)\n"
        "- note (ERROR, если страница не скачалась)\n"
        "Если ссылка битая — просто отметь error и иди дальше."
    ),
    expected_output="Корпус сырых данных по каждому URL (структурированный список блоков).",
    agent=reader,
)

# 2) Извлечение ключевых фактов
task2 = Task(
    description=(
        "На основе корпуса из Task1 извлечь по каждому домену:\n"
        "- УТП/позиционирование (1–3 предложения)\n"
        "- целевые сегменты (списком)\n"
        "- ассортимент/услуги (списком)\n"
        "- сигналы доверия (кейсы, отзывы, сертификаты, гарантия)\n"
        "- элементы конверсии (CTA, формы, офферы)\n"
        "- ориентировочные SEO-сигналы (Title/H1, если распознаваемы в тексте)\n"
        "Свести всё в единый структурированный список по конкурентам."
    ),
    expected_output="Структурированная выжимка фактов по конкурентам.",
    agent=extractor,
)

# 3) Сравнительный анализ
task3 = Task(
    description=(
        "Сравнить конкурентов между собой и составить аналитическую сводку:\n"
        "- для каждого конкурента выделить: сильные стороны, слабые стороны, уникальные особенности\n"
        "- общие тренды в нише (что делают все)\n"
        "- пробелы в нише (что никто не делает или делает плохо)\n"
        "- возможности для дифференциации\n"
        "- краткий SEO-скриншот (какие темы и ключи явно видны в текстах)\n"
    ),
    expected_output="Сравнительная таблица с сильными/слабыми сторонами каждого конкурента и возможностями для нашей стратегии.",
    agent=analyst,
)

# 4) Стратегические рекомендации для нашего бизнеса
task4 = Task(
    description=(
        "На основе анализа конкурентов сформировать стратегические рекомендации ДЛЯ НАШЕГО БИЗНЕСА:\n"
        "\n"
        "### Что позаимствовать у сильных конкурентов:\n"
        "- какие офферы/секции/подходы работают у конкурентов и стоит внедрить у нас\n"
        "- какие элементы конверсии показали эффективность\n"
        "- какие контент-стратегии приносят результат\n"
        "\n"
        "### Возможности для обгона (слабые стороны конкурентов):\n"
        "- какие пробелы в нише мы можем заполнить\n"
        "- где конкуренты слабы и мы можем выделиться\n"
        "- какие уникальные преимущества мы можем подчеркнуть\n"
        "\n"
        "### Конкретный план действий:\n"
        "- 5-7 приоритетных шагов для внедрения лучших практик\n"
        "- 10 тем для контента, которые помогут обойти конкурентов\n"
        "- план на 2 недели (спринт) — конкретные задачи\n"
    ),
    expected_output="Стратегические рекомендации для нашего бизнеса: что позаимствовать, как обойти конкурентов, план действий.",
    agent=strategist,
)

# -----------------------
# Компоновка Crew
# -----------------------

crew = Crew(
    agents=[reader, extractor, analyst, strategist],
    tasks=[task1, task2, task3, task4],
    verbose=True,
    process=Process.sequential,  # как в уроке
)

# -----------------------
# Простейший раннер
# -----------------------

def run_competitor_crew(urls: list[str]) -> str:
    """
    Принимает список ссылок конкурентов, выстраивает INPUT для Task1 и запускает процесс.
    Возвращает общий текстовый отчёт (то, что вернёт Crew по итогам).
    """
    # Небольшой prefetch, чтобы reader агенту было проще (не обязателен, но даст видимый прогресс).
    corpus = []
    for u in urls:
        html = fetch_html(u)
        text = extract_text(html)
        corpus.append({
            "url": u,
            "domain": domain_of(u),
            "excerpt": text[:1200] if not text.startswith("__ERROR_FETCH__") else "",
            "note": "OK" if not text.startswith("__ERROR_FETCH__") else text,
        })
        time.sleep(0.5)  # вежливость к сайтам

    # Передаём корпус как контекст в Task1 (через переменную окружения шага)
    # В CrewAI можно прокинуть через inputs=..., но чтобы остаться ближе к уроку —
    # просто положим в глобальную переменную окружения, а в описании Task1 объяснили формат.
    os.environ["INPUT_URLS"] = ",".join(urls)

    # Подпихнём черновик корпуса в description Task1 (чтобы ИИ видел структуру)
    # Создаем копию описания задачи, чтобы не модифицировать оригинал
    original_description = task1.description
    task1.description = original_description + (
        "\n---\nПример корпуса (сформирован заранее кодом):\n" + str(corpus)[:5000]
    )

    result = crew.kickoff()
    
    # Восстанавливаем оригинальное описание задачи
    task1.description = original_description
    
    return str(result)

def parse_competitor_summary(report_text: str) -> dict:
    """
    Парсит отчет и извлекает структурированные данные для графиков.
    Возвращает словарь с данными по доменам.
    """
    if not report_text:
        return {}
    
    # Простой парсинг с помощью регулярных выражений
    data = {}
    text_lower = report_text.lower()
    
    # Ищем упоминания доменов и связанных с ними данных
    import re
    from urllib.parse import urlparse
    
    # Паттерны для поиска данных
    patterns = {
        'text_size': [r'(\d+)\s*(?:символ|символов|знак|знаков)', r'длина.*?(\d+)', r'объем.*?(\d+)'],
        'ctas': [r'(\d+)\s*(?:cta|призыв|кнопк)', r'призыв.*?(\d+)', r'кнопк.*?(\d+)'],
        'trust_signals': [r'(\d+)\s*(?:отзыв|кейс|сертификат|гарантия)', r'доверие.*?(\d+)'],
        'has_cases': [r'кейс', r'пример', r'история успеха'],
        'has_reviews': [r'отзыв', r'рекомендация', r'мнение'],
        'has_certificates': [r'сертификат', r'лицензия', r'награда']
    }
    
    # Разбиваем текст на блоки по доменам
    lines = report_text.split('\n')
    current_domain = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Ищем упоминания URL или доменов
        url_match = re.search(r'https?://([^\s/]+)', line)
        if url_match:
            current_domain = url_match.group(1)
            if current_domain not in data:
                data[current_domain] = {
                    'text_size': 0,
                    'ctas': 0,
                    'trust_signals': 0,
                    'has_cases': False,
                    'has_reviews': False,
                    'has_certificates': False
                }
        
        # Если у нас есть текущий домен, ищем данные в строке
        if current_domain:
            for key, pattern_list in patterns.items():
                for pattern in pattern_list:
                    match = re.search(pattern, line.lower())
                    if match:
                        if key in ['has_cases', 'has_reviews', 'has_certificates']:
                            data[current_domain][key] = True
                        else:
                            try:
                                value = int(match.group(1))
                                if key == 'text_size':
                                    data[current_domain][key] = max(data[current_domain][key], value)
                                else:
                                    data[current_domain][key] += value
                            except (ValueError, IndexError):
                                pass
    
    # Если не нашли структурированных данных, создаем базовые значения
    if not data:
        # Ищем любые упоминания доменов в тексте
        domains = re.findall(r'https?://([^\s/]+)', report_text)
        for domain in set(domains):
            data[domain] = {
                'text_size': 10000,  # базовое значение
                'ctas': 3,
                'trust_signals': 2,
                'has_cases': 'кейс' in text_lower,
                'has_reviews': 'отзыв' in text_lower,
                'has_certificates': 'сертификат' in text_lower
            }
    
    return data

def build_charts(data: dict) -> list:
    """
    Создает графики на основе данных конкурентов.
    Возвращает список путей к созданным файлам.
    """
    if not data:
        return []
    
    chart_paths = []
    
    try:
        import matplotlib.pyplot as plt
        import plotly.express as px
        import plotly.graph_objects as go
        from pathlib import Path
        
        # Создаем папку для графиков
        charts_dir = Path("reports/charts")
        charts_dir.mkdir(parents=True, exist_ok=True)
        
        domains = list(data.keys())
        
        # График 1: Объем текста (Plotly)
        text_sizes = [data[domain].get('text_size', 0) for domain in domains]
        fig1 = go.Figure(data=[
            go.Bar(
                x=domains,
                y=text_sizes,
                marker_color='lightcoral',
                text=text_sizes,
                textposition='auto',
                name='Количество символов',
                hovertemplate='<b>%{x}</b><br>Символов: %{y}<extra></extra>'
            )
        ])
        fig1.update_layout(
            title={
                'text': "Объем текста по доменам",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16}
            },
            xaxis_title="Домен",
            yaxis_title="Количество символов",
            xaxis_tickangle=-45,
            height=500,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        chart1_path = charts_dir / "text_size.png"
        fig1.write_image(str(chart1_path), format="png", width=1200, height=700, scale=2)
        chart_paths.append(f"reports/charts/text_size.png")
        
        # График 2: CTA (Matplotlib)
        ctas = [data[domain].get('ctas', 0) for domain in domains]
        plt.figure(figsize=(12, 6))
        bars = plt.bar(domains, ctas, color='skyblue', edgecolor='navy', alpha=0.7)
        
        for bar, cta in zip(bars, ctas):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                    str(cta), ha='center', va='bottom', fontweight='bold')
        
        plt.title("Количество CTA по доменам", fontsize=16, fontweight='bold', pad=20)
        plt.xlabel("Домен", fontsize=12, fontweight='bold')
        plt.ylabel("Количество CTA", fontsize=12, fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        chart2_path = charts_dir / "ctas.png"
        plt.savefig(str(chart2_path), dpi=200, bbox_inches='tight')
        plt.close()
        chart_paths.append(f"reports/charts/ctas.png")
        
        # График 3: Сигналы доверия (Plotly)
        trust_signals = [data[domain].get('trust_signals', 0) for domain in domains]
        fig3 = go.Figure(data=[
            go.Bar(
                x=domains,
                y=trust_signals,
                marker_color='lightgreen',
                text=trust_signals,
                textposition='auto',
                name='Сигналы доверия',
                hovertemplate='<b>%{x}</b><br>Сигналов доверия: %{y}<extra></extra>'
            )
        ])
        fig3.update_layout(
            title={
                'text': "Количество сигналов доверия по доменам",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16}
            },
            xaxis_title="Домен",
            yaxis_title="Количество сигналов",
            xaxis_tickangle=-45,
            height=500,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        chart3_path = charts_dir / "trust_signals.png"
        fig3.write_image(str(chart3_path), format="png", width=1200, height=700, scale=2)
        chart_paths.append(f"reports/charts/trust_signals.png")
        
    except Exception as e:
        print(f"Ошибка при создании графиков: {e}")
        # Возвращаем пустой список если не удалось создать графики
        pass
    
    return chart_paths

if __name__ == "__main__":
    urls = [
        "https://example.com/",
        "https://www.example.org/",
    ]
    report = run_competitor_crew(urls)
    print("\n=== COMPETITOR REPORT ===\n")
    print(report)

    # ➕ Сохранение PDF
    sections = make_sections_from_result(report)
    pdf_path = save_pdf_report(
        title="Анализ конкурентов — автогенерируемый отчёт",
        sections=sections,
        table_blocks=None,  # сюда позже можно передавать таблицы
        # output_path="reports/my_custom_name.pdf"  # не обязательно
    )
    print(f"\nPDF сохранён: {pdf_path}")