import { useCallback, useEffect, useState } from 'react'
import { getHealth, getRecommendations, getForecast } from '../api'
import Header from '../components/Header'
import Navigation from '../components/Navigation'
import RecommendationCard from '../components/RecommendationCard'
import QuickInsights from '../components/QuickInsights'
import ErrorState from '../components/ErrorState'

export default function StudyPlanner() {
  const [health, setHealth] = useState(null)
  const [recommendations, setRecommendations] = useState(null)
  const [forecastData, setForecastData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadPlanner = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const [healthResult, recommendationsResult, forecastResult] =
        await Promise.all([
          getHealth().catch(() => null),
          getRecommendations(),
          getForecast(),
        ])

      setHealth(healthResult)
      setRecommendations(recommendationsResult?.recommendations ?? null)
      setForecastData(forecastResult)
    } catch (err) {
      setError(err.message || 'Unable to load study recommendations.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadPlanner()
  }, [loadPlanner])

  return (
    <div className="dashboard">
      <Header health={health} />
      <Navigation />

      <section className="hero">
        <div className="hero__content">
          <span className="hero__badge">Smart Study Planning</span>
          <h2 className="hero__title">Find Your Best Study Time</h2>
          <p className="hero__text">
            Discover quieter study windows using predicted library occupancy.
          </p>
        </div>
      </section>

      <main className="page-section">
        {error ? (
          <ErrorState message={error} onRetry={loadPlanner} />
        ) : (
          <>
            <QuickInsights
              insights={forecastData?.insights}
              loading={loading}
            />

            <div className="dashboard-grid__recs">
              <RecommendationCard
                recommendations={recommendations}
                loading={loading}
                weatherAware={forecastData?.weather_adjustment_enabled}
              />
            </div>
          </>
        )}
      </main>
    </div>
  )
}