import LoadingState from './LoadingState'

export default function ModelPerformance({ metrics, note, loading }) {
  if (loading) {
    return (
      <section className="section">
        <LoadingState variant="card-medium" />
      </section>
    )
  }

  const entries = metrics ? Object.entries(metrics) : []

  return (
    <section className="section">
      <div className="metrics-section">
        <div className="section-header">
          <div>
            <h2 className="section-title">Prediction Model Performance</h2>
            <p className="section-subtitle">Evaluation metrics from the trained prediction model</p>
          </div>
        </div>

        {entries.length === 0 ? (
          <div className="empty-state">No model metrics available.</div>
        ) : (
          <>
            <div className="metrics-grid">
              {entries.map(([label, value]) => (
                <div key={label} className="metric-card">
                  <span className="metric-card__label">{label}</span>
                  <span className="metric-card__value">
                    {typeof value === 'number'
                      ? label.includes('Score') || label.includes('R²')
                        ? value.toFixed(3)
                        : value.toFixed(1)
                      : value}
                  </span>
                </div>
              ))}
            </div>
            {note && <p className="metrics-note">{note}</p>}
          </>
        )}
      </div>
    </section>
  )
}
