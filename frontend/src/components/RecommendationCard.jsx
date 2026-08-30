import LoadingState from './LoadingState'
import { statusLabel, statusColor } from '../utils/helpers'

export default function RecommendationCard({ recommendations, loading, weatherAware }) {
  if (loading) {
    return (
      <section className="section">
        <LoadingState variant="card-large" />
      </section>
    )
  }

  if (!recommendations?.length) {
    return (
      <section className="section">
        <div className="recommendations-section">
          <div className="section-header">
            <div>
              <h2 className="section-title">Smart Study Recommendations</h2>
              <p className="section-subtitle">
                {weatherAware
                  ? 'Best times using the weather-adjusted occupancy estimate'
                  : 'Best times to visit based on predicted crowd levels'}
              </p>
            </div>
          </div>
          <div className="empty-state">No recommendations available for the current forecast period.</div>
        </div>
      </section>
    )
  }

  return (
    <section className="section">
      <div className="recommendations-section">
        <div className="section-header">
          <div>
            <h2 className="section-title">Smart Study Recommendations</h2>
            <p className="section-subtitle">
                {weatherAware
                  ? 'Best times using the weather-adjusted occupancy estimate'
                  : 'Best times to visit based on predicted crowd levels'}
              </p>
          </div>
        </div>

        <div className="recommendations-grid">
          {recommendations.map((rec, idx) => (
            <div key={idx} className={`recommendation-card ${idx === 0 ? 'recommendation-card--primary' : ''}`}>
              <span className="recommendation-card__badge">
                {idx === 0 ? 'Best Time to Visit' : 'Also Recommended'}
              </span>
              <p className="recommendation-card__time">
                {rec.start_time} – {rec.end_time}
              </p>
              <div className="recommendation-card__details">
                <div>
                  <span className="recommendation-card__label">Estimated occupancy</span>
                  <span className="recommendation-card__value">{rec.estimated_occupancy} students</span>
                </div>
                <div>
                  <span className="recommendation-card__label">Crowd level</span>
                  <span
                    className="recommendation-card__status"
                    style={{ color: statusColor(rec.crowd_level) }}
                  >
                    {statusLabel(rec.crowd_level)}
                  </span>
                </div>
                {rec.weather && (
                  <div>
                    <span className="recommendation-card__label">Weather</span>
                    <span className="recommendation-card__value">{rec.weather}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        <p className="recommendations-cta">
          Plan your next study session during these quieter periods.
        </p>
      </div>
    </section>
  )
}
