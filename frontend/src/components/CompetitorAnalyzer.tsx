import React, { useState } from 'react'
import './CompetitorAnalyzer.css'

interface AnalyzeResponse {
  report_text: string
  pdf_path: string
  charts: string[]
}

const API_BASE = 'http://localhost:8000'

const CompetitorAnalyzer: React.FC = () => {
  const [urls, setUrls] = useState<string[]>([])
  const [urlInput, setUrlInput] = useState('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [result, setResult] = useState<AnalyzeResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const addUrl = () => {
    if (urlInput.trim() && !urls.includes(urlInput.trim())) {
      setUrls([...urls, urlInput.trim()])
      setUrlInput('')
    }
  }

  const removeUrl = (index: number) => {
    setUrls(urls.filter((_, i) => i !== index))
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      addUrl()
    }
  }

  const analyzeCompetitors = async () => {
    if (urls.length === 0) {
      setError('Добавьте хотя бы один URL для анализа')
      return
    }

    setIsAnalyzing(true)
    setError(null)
    setResult(null)

    try {
      const response = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ urls }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Ошибка при анализе')
      }

      const data: AnalyzeResponse = await response.json()
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const downloadPDF = () => {
    if (result?.pdf_path) {
      window.open(`${API_BASE}/api/download?path=${encodeURIComponent(result.pdf_path)}`, '_blank')
    }
  }

  return (
    <div className="competitor-analyzer">
      <div className="input-section">
        <h2>Добавьте URL конкурентов</h2>
        <div className="url-input">
          <input
            type="url"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Введите URL сайта конкурента"
            className="url-field"
          />
          <button onClick={addUrl} className="add-btn">
            Добавить
          </button>
        </div>

        {urls.length > 0 && (
          <div className="url-list">
            <h3>Список URL для анализа:</h3>
            <ul>
              {urls.map((url, index) => (
                <li key={index} className="url-item">
                  <span className="url-text">{url}</span>
                  <button
                    onClick={() => removeUrl(index)}
                    className="remove-btn"
                    title="Удалить"
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        <button
          onClick={analyzeCompetitors}
          disabled={isAnalyzing || urls.length === 0}
          className="analyze-btn"
        >
          {isAnalyzing ? 'Анализируем...' : 'Запустить анализ'}
        </button>
      </div>

      {error && (
        <div className="error-message">
          <h3>Ошибка:</h3>
          <p>{error}</p>
        </div>
      )}

      {result && (
        <div className="results-section">
          <h2>Результаты анализа</h2>
          
          <div className="report-preview">
            <h3>Краткая сводка:</h3>
            <div className="report-text">
              {result.report_text}
            </div>
          </div>

          {result.charts && result.charts.length > 0 && (
            <div className="charts-section">
              <h3>Визуализация:</h3>
              <div className="charts-grid">
                {result.charts.map((chart, index) => (
                  <div key={index} className="chart-item">
                    <img
                      src={`${API_BASE}/charts/${chart.split('/').pop()}`}
                      alt={`График ${index + 1}`}
                      className="chart-image"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="download-section">
            <button onClick={downloadPDF} className="download-btn">
              📄 Скачать отчёт PDF
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default CompetitorAnalyzer
