import { useEffect, useState } from 'react'
import { getHealth, getForecast } from '../api'
import Header from '../components/Header'
import Navigation from '../components/Navigation'
import ForecastChart from '../components/ForecastChart'
import ErrorState from '../components/ErrorState'

const FORECAST_PERIODS = [
  { id: '24h', label: '24 Hours' },
  { id: '7d', label: '7 Days' },
]

export default function CrowdPredictions() {
  const [health, setHealth] = useState(null)
  const [forecastData, setForecastData] = useState(null)
  const [period, setPeriod] = useState('24h')
  const [retryCount, setRetryCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let active = true

    async function loadPredictions() {
      setLoading(true)
      setError(null)

      try {
        const [healthResult, forecastResult] = await Promise.all([
          getHealth().catch(() => null),
          getForecast(period),
        ])

        if (active) {
          setHealth(healthResult)
          setForecastData(forecastResult)
        }
      } catch (err) {
        if (active) {
          setForecastData(null)
          setError(err.message || 'Unable to load crowd predictions.')
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    loadPredictions()
    return () => {
      active = false
    }
  }, [period, retryCount])

  return (
    <div className="dashboard">
      <Header health={health} />
      <Navigation />

      <section className="hero">
        <div className="hero__content">
          <span className="hero__badge">Crowd Forecasting</span>
          <h2 className="hero__title">Crowd Predictions</h2>
          <p className="hero__text">
            Explore model-predicted occupancy percentages for upcoming hours and days.
          </p>
        </div>
      </section>

      <main className="page-section">
        <div className="forecast-period-control">
          <span className="forecast-period-control__label">Forecast horizon</span>
          <div className="forecast-period-toggle" role="group" aria-label="Forecast horizon">
            {FORECAST_PERIODS.map((option) => (
              <button
                key={option.id}
                type="button"
                className={`forecast-period-toggle__button${period === option.id ? ' is-active' : ''}`}
                aria-pressed={period === option.id}
                onClick={() => setPeriod(option.id)}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        {error ? (
          <ErrorState
            message={error}
            onRetry={() => setRetryCount((count) => count + 1)}
          />
        ) : (
          <ForecastChart
            forecast={forecastData?.forecast}
            capacity={forecastData?.forecast?.[0]?.capacity || 200}
            loading={loading}
            weatherAdjusted={forecastData?.weather_adjustment_enabled}
            adjustmentNote={forecastData?.weather_adjustment_note}
            aggregation={forecastData?.aggregation}
            period={period}
            valueMode="percentage"
            intervalHours={2}
          />
        )}
      </main>
    </div>
  )
}
