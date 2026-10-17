import { useCallback, useEffect, useState } from 'react'
import { getHealth, getMetrics, getDataSources } from '../api'
import Header from '../components/Header'
import Navigation from '../components/Navigation'
import ModelPerformance from '../components/ModelPerformance'
import DataSources from '../components/DataSources'
import ErrorState from '../components/ErrorState'

export default function ModelEvaluation() {
  const [health, setHealth] = useState(null)
  const [metricsData, setMetricsData] = useState(null)
  const [dataSources, setDataSources] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadEvaluation = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const [healthResult, metricsResult, sourcesResult] = await Promise.all([
        getHealth().catch(() => null),
        getMetrics(),
        getDataSources(),
      ])

      setHealth(healthResult)
      setMetricsData(metricsResult)
      setDataSources(sourcesResult?.sources ?? null)
    } catch (err) {
      setError(err.message || 'Unable to load model evaluation.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadEvaluation()
  }, [loadEvaluation])

  return (
    <div className="dashboard">
      <Header health={health} />
      <Navigation />

      <section className="hero">
        <div className="hero__content">
          <span className="hero__badge">Research & Evaluation</span>
          <h2 className="hero__title">Prediction Model Evaluation</h2>
          <p className="hero__text">
            Review the model's evaluation metrics, dataset information, and system data sources.
          </p>
        </div>
      </section>

      <main className="page-section">
        {error ? (
          <ErrorState message={error} onRetry={loadEvaluation} />
        ) : (
          <>
            <ModelPerformance
              metrics={metricsData?.metrics}
              note={metricsData?.note}
              loading={loading}
            />

            <DataSources sources={dataSources} />
          </>
        )}
      </main>
    </div>
  )
}