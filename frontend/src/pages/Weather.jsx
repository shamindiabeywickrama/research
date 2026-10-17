import { useCallback, useEffect, useState } from 'react'
import { getHealth, getCurrentWeather, getForecast } from '../api'
import Header from '../components/Header'
import Navigation from '../components/Navigation'
import WeatherCard from '../components/WeatherCard'
import WeatherImpact from '../components/WeatherImpact'
import WeatherTimeline from '../components/WeatherTimeline'
import ErrorState from '../components/ErrorState'

export default function Weather() {
  const [health, setHealth] = useState(null)
  const [weather, setWeather] = useState(null)
  const [forecast, setForecast] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadWeather = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const [healthResult, weatherResult, forecastResult] =
        await Promise.all([
          getHealth().catch(() => null),
          getCurrentWeather(),
          getForecast(),
        ])

      setHealth(healthResult)
      setWeather(weatherResult)
      setForecast(forecastResult?.forecast ?? [])
    } catch (err) {
      setError(err.message || 'Unable to load weather information.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadWeather()
  }, [loadWeather])

  return (
    <div className="dashboard">
      <Header health={health} />
      <Navigation />

      <section className="hero">
        <div className="hero__content">
          <span className="hero__badge">Weather Awareness</span>
          <h2 className="hero__title">Weather Conditions</h2>
          <p className="hero__text">
            View current weather and understand its estimated impact on library visits.
          </p>
        </div>
      </section>

      <main className="page-section">
        {error ? (
          <ErrorState message={error} onRetry={loadWeather} />
        ) : (
          <>
            <WeatherCard weather={weather} loading={loading} />
            <WeatherImpact weather={weather} />
            <WeatherTimeline forecast={forecast} />
          </>
        )}
      </main>
    </div>
  )
}