import { useCallback, useEffect, useState } from 'react'
import {
  getHealth,
  getCurrentOccupancy,
  getForecast,
  getRecommendations,
  getMetrics,
  getDataSources,
} from '../api'
import Header from '../components/Header'
import CurrentOccupancy from '../components/CurrentOccupancy'
import QuickInsights from '../components/QuickInsights'
import ForecastChart from '../components/ForecastChart'
import RecommendationCard from '../components/RecommendationCard'
import CrowdTimeline from '../components/CrowdTimeline'
import ModelPerformance from '../components/ModelPerformance'
import DataSources from '../components/DataSources'
import WiFiStatus from '../components/WiFiStatus'
import NetworkActivity from '../components/NetworkActivity'
import Footer from '../components/Footer'
import ErrorState from '../components/ErrorState'

export default function Dashboard() {
  const [health, setHealth] = useState(null)
  const [current, setCurrent] = useState(null)
  const [forecastData, setForecastData] = useState(null)
  const [recommendations, setRecommendations] = useState(null)
  const [metricsData, setMetricsData] = useState(null)
  const [dataSources, setDataSources] = useState(null)
  const [dataMode, setDataMode] = useState('demo')
  const [loading, setLoading] = useState(true)
  const [forecastError, setForecastError] = useState(null)
  const [serviceError, setServiceError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setServiceError(null)
    setForecastError(null)

    try {
      const [healthRes, currentRes, forecastRes, recsRes, metricsRes, sourcesRes] =
        await Promise.all([
          getHealth().catch(() => null),
          getCurrentOccupancy().catch(() => null),
          getForecast().catch((e) => {
            setForecastError(e.message)
            return null
          }),
          getRecommendations().catch(() => null),
          getMetrics().catch(() => null),
          getDataSources().catch(() => null),
        ])

      if (!healthRes && !currentRes && !forecastRes) {
        setServiceError('Library prediction service is currently unavailable.')
      }

      setHealth(healthRes)
      setCurrent(currentRes)
      setForecastData(forecastRes)
      setRecommendations(recsRes?.recommendations ?? null)
      setMetricsData(metricsRes)
      setDataSources(sourcesRes?.sources ?? null)
      setDataMode(
        currentRes?.data_mode ||
        forecastRes?.data_mode ||
        healthRes?.data_mode ||
        'demo',
      )
      setLastUpdated(new Date().toISOString())
    } catch {
      setServiceError('Library prediction service is currently unavailable.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [loadData])

  const capacity = current?.capacity || forecastData?.forecast?.[0]?.capacity || 200

  return (
    <div className="dashboard">
      <Header health={health} lastUpdated={lastUpdated} />

      {serviceError && (
        <div className="service-banner">
          <ErrorState message={serviceError} onRetry={loadData} />
        </div>
      )}

      <section className="hero">
        <div className="hero__content">
          <span className="hero__badge">Machine Learning Powered</span>
          <h2 className="hero__title">Plan Your Study Time Smarter</h2>
          <p className="hero__text">
            Real-time occupancy, 24-hour crowd forecasts, and quieter study windows
            in one dashboard.
          </p>
        </div>
      </section>

      <div className="dashboard-grid">
        <div className="dashboard-grid__occupancy">
          <CurrentOccupancy
            data={current}
            loading={loading && !current}
            dataMode={dataMode}
          />
        </div>

        <div className="dashboard-grid__insights">
          <QuickInsights
            insights={forecastData?.insights}
            loading={loading && !forecastData}
            currentData={current}
          />
        </div>

        {dataMode === 'wifi' && (
          <>
            <div className="dashboard-grid__wifi">
              <WiFiStatus dataMode={dataMode} />
            </div>
            <div className="dashboard-grid__activity">
              <NetworkActivity dataMode={dataMode} />
            </div>
          </>
        )}

        <div className="dashboard-grid__chart">
          <ForecastChart
            forecast={forecastData?.forecast}
            capacity={capacity}
            loading={loading && !forecastData && !forecastError}
            error={forecastError}
            onRetry={loadData}
          />
        </div>

        <div className="dashboard-grid__recs">
          <RecommendationCard
            recommendations={recommendations}
            loading={loading && !recommendations}
          />
        </div>

        {forecastData?.forecast?.length ? (
          <div className="dashboard-grid__timeline">
            <CrowdTimeline forecast={forecastData.forecast} />
          </div>
        ) : null}

        <div className="dashboard-grid__metrics">
          <ModelPerformance
            metrics={metricsData?.metrics}
            note={metricsData?.note}
            loading={loading && !metricsData}
          />
        </div>

        <div className="dashboard-grid__sources">
          <DataSources sources={dataSources} />
        </div>
      </div>

      <Footer />
    </div>
  )
}
