import React, { useState } from 'react'
import './App.css'
import CompetitorAnalyzer from './components/CompetitorAnalyzer'

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>Анализ конкурентов</h1>
        <p>Автоматический анализ конкурентов с помощью AI-агентов</p>
      </header>
      <main>
        <CompetitorAnalyzer />
      </main>
    </div>
  )
}

export default App