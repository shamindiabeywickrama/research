import { useEffect, useState } from 'react'
import { getRoot, predictHour, predictDay, getHistory } from './api'
import DayForecastChart from './components/DayForecastChart'
import HistoryTable from './components/HistoryTable'

function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

function currentHour() {
  const h = new Date().getHours()
  return Math.min(19, Math.max(8, h))
}

export default function App() {
  const [apiStatus, setApiStatus] = useState(null)
  const [date, setDate] = useState(todayStr())
  const [hour, setHour] = useState(currentHour())
  const [current, setCurrent] = useState(null)
  const [dayData, setDayData] = useState([])
  const [history, setHistory] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getRoot().then(setApiStatus).catch(() => setApiStatus({ supabase_connected: false, offline: true }))
    refreshHistory()
  }, [])

  async function refreshHistory() {
    try {
      const rows = await getHistory(10)
      setHistory(rows)
    } catch (e) {
      // history is optional; ignore quietly if supabase isn't set up
    }
  }

  async function handleGenerate() {
    setError(null)
    setLoading(true)
    try {
      const [single, day] = await Promise.all([
        predictHour(date, Number(hour)),
        predictDay(date),
      ])
      setCurrent(single)
      setDayData(day)
      refreshHistory()
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const online = apiStatus && !apiStatus.offline

  return (
    <div className="app-shell">
      <header className="masthead">
        <div>
          <span className="eyebrow">Reading Room Forecast</span>
          <h1>Library Crowd Predictor</h1>
        </div>
        <span className={`status-pill ${online ? 'online' : 'offline'}`}>
          {online ? '● API connected' : '○ API offline'}
        </span>
      </header>

      <div className="info-banner">
        <strong>How this works —</strong> no cameras or occupancy sensors are used.
        A model trained on historical attendance patterns (time of day, weekday vs
        weekend, exam weeks, semester breaks) predicts how busy the library is
        likely to be, purely from calendar context.
      </div>

      {error && <div className="error-banner">⚠ {error}</div>}

      <div className="controls-row">
        <div className="field">
          <label htmlFor="date">Date</label>
          <input id="date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="hour">Hour (8–19)</label>
          <input
            id="hour"
            type="number"
            min="8"
            max="19"
            value={hour}
            onChange={(e) => setHour(e.target.value)}
          />
        </div>
        <button className="primary" onClick={handleGenerate} disabled={loading}>
          {loading ? 'Predicting…' : 'Generate forecast'}
        </button>
      </div>

      <div className="hero-grid">
        <div className="card hero-number-card">
          <div>
            <div className="label">Selected hour</div>
            <div className="hero-number">
              {current ? current.predicted_occupancy_percent : '—'}
              <span className="unit">%</span>
            </div>
            <div className="hero-sub">
              {current
                ? `≈ ${current.predicted_occupancy_count} of ${current.capacity} seats occupied at ${String(current.hour).padStart(2, '0')}:00 on ${current.date}`
                : 'Pick a date and hour, then generate a forecast.'}
            </div>
          </div>
          {current && (
            <div className="tag-row">
              {current.is_exam_period && <span className="tag exam">Exam period</span>}
              {current.is_semester_break && <span className="tag">Semester break</span>}
              {current.is_weekend && <span className="tag weekend">Weekend</span>}
              {!current.is_exam_period && !current.is_semester_break && !current.is_weekend && (
                <span className="tag">Regular weekday</span>
              )}
            </div>
          )}
        </div>

        <div className="card">
          <div className="section-title">Full day forecast</div>
          <DayForecastChart data={dayData} />
        </div>
      </div>

      <section className="chart-card">
        <div className="section-title">Recent predictions</div>
        <div className="card">
          <HistoryTable rows={history} />
        </div>
      </section>

      <p className="footer-note">
        Library Crowd Prediction System — synthetic dataset · RandomForest model · FastAPI · Supabase · React
      </p>
    </div>
  )
}
