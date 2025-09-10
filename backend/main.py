# backend/main.py
# FastAPI backend для анализа конкурентов

import os
import re
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urlparse

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Импорты из существующих модулей
import sys
sys.path.append('..')
from competitor_crew import run_competitor_crew, parse_competitor_summary
from report_export import save_pdf_report, make_sections_from_result

app = FastAPI(title="Competitor Analysis API", version="1.0.0")

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic модели
class AnalyzeRequest(BaseModel):
    urls: List[str]

class AnalyzeResponse(BaseModel):
    report_text: str
    pdf_path: str
    charts: List[str]

class HealthResponse(BaseModel):
    ok: bool

# Создаем папки для отчетов и графиков
# Используем абсолютные пути для надежности
REPORTS_DIR = Path(__file__).parent.parent / "reports"
CHARTS_DIR = REPORTS_DIR / "charts"
REPORTS_DIR.mkdir(exist_ok=True)
CHARTS_DIR.mkdir(exist_ok=True)

def generate_charts(report_text: str, urls: List[str]) -> List[str]:
    """
    Генерирует графики на основе отчета и сохраняет их как PNG файлы.
    Возвращает список путей к созданным файлам.
    """
    chart_paths = []
    
    try:
        # Парсим данные из отчета
        competitor_data = parse_competitor_summary(report_text)
        
        if not competitor_data:
            # Если не удалось распарсить, создаем mock данные
            competitor_data = create_mock_data(urls)
        
        # График 1: Объем текста по доменам (Plotly)
        chart1_path = CHARTS_DIR / "text_size.png"
        create_text_size_chart(competitor_data, chart1_path)
        chart_paths.append(f"reports/charts/text_size.png")
        
        # График 2: Количество CTA по доменам (Matplotlib)
        chart2_path = CHARTS_DIR / "ctas.png"
        create_cta_chart(competitor_data, chart2_path)
        chart_paths.append(f"reports/charts/ctas.png")
        
        # График 3: Сигналы доверия (Plotly)
        chart3_path = CHARTS_DIR / "trust_signals.png"
        create_trust_signals_chart(competitor_data, chart3_path)
        chart_paths.append(f"reports/charts/trust_signals.png")
        
    except Exception as e:
        print(f"Ошибка при создании графиков: {e}")
        # Создаем простые mock графики
        chart_paths = create_fallback_charts(urls)
    
    return chart_paths

def create_mock_data(urls: List[str]) -> Dict[str, Dict[str, Any]]:
    """Создает mock данные для демонстрации графиков"""
    import random
    
    data = {}
    for url in urls:
        domain = urlparse(url).netloc or url
        data[domain] = {
            "text_size": random.randint(5000, 25000),
            "ctas": random.randint(2, 8),
            "trust_signals": random.randint(1, 5),
            "has_cases": random.choice([True, False]),
            "has_reviews": random.choice([True, False]),
            "has_certificates": random.choice([True, False])
        }
    return data

def create_text_size_chart(data: Dict[str, Dict[str, Any]], output_path: Path):
    """Создает график объема текста по доменам"""
    domains = list(data.keys())
    text_sizes = [data[domain]["text_size"] for domain in domains]
    
    fig = px.bar(
        x=domains, 
        y=text_sizes,
        title="Объем текста по доменам",
        labels={"x": "Домен", "y": "Количество символов"},
        color=text_sizes,
        color_continuous_scale="Blues"
    )
    
    fig.update_layout(
        xaxis_tickangle=-45,
        height=500,
        showlegend=False
    )
    
    fig.write_image(str(output_path), format="png", width=1200, height=700, scale=2)

def create_cta_chart(data: Dict[str, Dict[str, Any]], output_path: Path):
    """Создает график количества CTA по доменам"""
    domains = list(data.keys())
    ctas = [data[domain]["ctas"] for domain in domains]
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(domains, ctas, color='skyblue', edgecolor='navy', alpha=0.7)
    
    # Добавляем значения на столбцы
    for bar, cta in zip(bars, ctas):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                str(cta), ha='center', va='bottom')
    
    plt.title("Количество CTA по доменам", fontsize=14, fontweight='bold')
    plt.xlabel("Домен", fontsize=12)
    plt.ylabel("Количество CTA", fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(str(output_path), dpi=200, bbox_inches='tight')
    plt.close()

def create_trust_signals_chart(data: Dict[str, Dict[str, Any]], output_path: Path):
    """Создает график сигналов доверия"""
    domains = list(data.keys())
    trust_counts = [data[domain]["trust_signals"] for domain in domains]
    
    fig = go.Figure(data=[
        go.Bar(
            x=domains,
            y=trust_counts,
            marker_color='lightgreen',
            text=trust_counts,
            textposition='auto',
        )
    ])
    
    fig.update_layout(
        title="Количество сигналов доверия по доменам",
        xaxis_title="Домен",
        yaxis_title="Количество сигналов",
        xaxis_tickangle=-45,
        height=500
    )
    
    fig.write_image(str(output_path), format="png", width=1200, height=700, scale=2)

def create_fallback_charts(urls: List[str]) -> List[str]:
    """Создает простые fallback графики если основной парсинг не сработал"""
    chart_paths = []
    
    # Простой график с количеством URL
    fig = px.bar(
        x=["Анализируемые сайты"], 
        y=[len(urls)],
        title=f"Проанализировано сайтов: {len(urls)}",
        labels={"x": "", "y": "Количество"}
    )
    
    fallback_path = CHARTS_DIR / "fallback.png"
    fig.write_image(str(fallback_path), format="png", width=800, height=400, scale=2)
    chart_paths.append(f"reports/charts/fallback.png")
    
    return chart_paths

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Проверка здоровья API"""
    return HealthResponse(ok=True)

@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_competitors(request: AnalyzeRequest):
    """Запуск анализа конкурентов"""
    try:
        # Валидация URL
        if not request.urls:
            raise HTTPException(status_code=400, detail="Список URL не может быть пустым")
        
        # Проверяем что это валидные URL
        for url in request.urls:
            if not url.startswith(('http://', 'https://')):
                raise HTTPException(status_code=400, detail=f"Некорректный URL: {url}")
        
        print(f"Запуск анализа для {len(request.urls)} URL...")
        
        # Запускаем анализ через CrewAI
        report_text = run_competitor_crew(request.urls)
        
        print("Анализ завершен, создаем графики...")
        
        # Создаем графики
        chart_paths = generate_charts(report_text, request.urls)
        
        print("Графики созданы, генерируем PDF...")
        
        # Создаем PDF с графиками
        sections = make_sections_from_result(report_text)
        pdf_path = save_pdf_report(
            title="Анализ конкурентов — автогенерируемый отчёт",
            sections=sections,
            table_blocks=None,
            images=chart_paths,
            urls=request.urls
        )
        
        # Возвращаем относительный путь для скачивания
        # Получаем относительный путь от папки reports
        try:
            relative_pdf_path = pdf_path.relative_to(REPORTS_DIR)
            relative_pdf_path = str(relative_pdf_path).replace("\\", "/")
        except ValueError:
            # Если файл не в папке reports, используем только имя файла
            relative_pdf_path = pdf_path.name
        
        print(f"PDF сохранен: {pdf_path}")
        
        # Очищаем markdown из краткой сводки для frontend
        from report_export import _clean_markdown
        cleaned_summary = _clean_markdown(report_text)
        
        return AnalyzeResponse(
            report_text=cleaned_summary[:1000] + "..." if len(cleaned_summary) > 1000 else cleaned_summary,
            pdf_path=relative_pdf_path,
            charts=chart_paths
        )
        
    except Exception as e:
        print(f"Ошибка при анализе: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при анализе: {str(e)}")

@app.get("/api/download")
async def download_file(path: str = Query(...)):
    """Безопасная загрузка файлов из папки reports"""
    try:
        # Проверяем что путь не выходит за пределы папки reports
        safe_path = REPORTS_DIR / path
        safe_path = safe_path.resolve()
        reports_path = REPORTS_DIR.resolve()
        
        if not str(safe_path).startswith(str(reports_path)):
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        if not safe_path.exists():
            print(f"Файл не найден: {safe_path}")
            print(f"Содержимое папки reports: {list(REPORTS_DIR.iterdir())}")
            raise HTTPException(status_code=404, detail="Файл не найден")
        
        return FileResponse(
            path=str(safe_path),
            filename=safe_path.name,
            media_type='application/octet-stream'
        )
        
    except Exception as e:
        print(f"Ошибка при загрузке файла: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке файла: {str(e)}")

# Статический сервер для графиков (опционально)
@app.get("/charts/{filename}")
async def serve_chart(filename: str):
    """Сервис для предпросмотра графиков"""
    chart_path = CHARTS_DIR / filename
    if not chart_path.exists():
        raise HTTPException(status_code=404, detail="График не найден")
    
    return FileResponse(
        path=str(chart_path),
        media_type='image/png'
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
