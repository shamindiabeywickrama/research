import { weatherIcon } from '../utils/weather'

export default function WeatherImpact({ weather }) {
  const available = Boolean(weather?.available)
  const impact = weather?.impact
  const condition = weather?.condition || '—'
  const temp = weather?.temperature
  const rainProb = weather?.precipitation_probability

  return (
    <section className="section">
      <div className="weather-impact-card">
        <div className="section-header">
          <div>
            <h2 className="section-title">Weather Impact</h2>
            <p className="section-subtitle">Weather-adjusted estimate context</p>
          </div>
        </div>

        {!available ? (
          <p className="panel__muted">Weather data temporarily unavailable.</p>
        ) : (
          <>
            <div className="weather-impact-grid">
              <div className="wifi-status-item">
                <span className="wifi-status-item__label">Current weather</span>
                <span className="wifi-status-item__value">
                  {weatherIcon(condition)} {condition}
                </span>
              </div>
              <div className="wifi-status-item">
                <span className="wifi-status-item__label">Temperature</span>
                <span className="wifi-status-item__value">
                  {temp != null ? `${Math.round(temp)}°C` : '—'}
                </span>
              </div>
              <div className="wifi-status-item">
                <span className="wifi-status-item__label">Rain probability</span>
                <span className="wifi-status-item__value">
                  {rainProb != null ? `${rainProb}%` : '—'}
                </span>
              </div>
              <div className="wifi-status-item">
                <span className="wifi-status-item__label">Expected library impact</span>
                <span className="wifi-status-item__value">
                  {impact?.impact_label || 'Low expected impact'}
                </span>
              </div>
            </div>
            <p className="weather-impact-note">
              Weather conditions may influence indoor study demand.
              {impact?.prototype
                ? ' Shown as a weather-adjusted estimate using prototype assumptions.'
                : ''}
            </p>
          </>
        )}
      </div>
    </section>
  )
}
