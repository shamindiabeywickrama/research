import LoadingState from './LoadingState'
import { weatherIcon } from '../utils/weather'

const TOOLTIP =
  'Weather is used as an additional contextual signal because weather conditions may influence students’ library usage patterns. This prototype uses a configurable weather adjustment because the trained model does not include weather features.'

export default function WeatherCard({ weather, loading }) {
  if (loading) {
    return (
      <section className="section">
        <LoadingState variant="card-large" />
      </section>
    )
  }

  const available = Boolean(weather?.available)
  const condition = weather?.condition || 'Unavailable'
  const temp = weather?.temperature
  const rainProb = weather?.precipitation_probability
  const impact = weather?.impact

  return (
    <section className="section">
      <div className="weather-card">
        <div className="section-header">
          <div>
            <h2 className="section-title">Weather Today</h2>
            <p className="section-subtitle">
              Live weather
              {weather?.provider ? ` · Powered by ${weather.provider}` : ''}
            </p>
          </div>
          <span
            className={`weather-service-status ${
              available ? 'weather-service-status--on' : 'weather-service-status--off'
            }`}
          >
            {available ? '● Connected' : '○ Unavailable'}
          </span>
        </div>

        {!available ? (
          <p className="panel__muted">Weather data temporarily unavailable.</p>
        ) : (
          <div className="weather-card__body">
            <div className="weather-card__hero">
              <span className="weather-card__icon" aria-hidden="true">
                {weatherIcon(condition)}
              </span>
              <div>
                <p className="weather-card__temp">
                  {temp != null ? `${Math.round(temp)}°C` : '—'}
                </p>
                <p className="weather-card__condition">{condition}</p>
              </div>
            </div>
            <div className="weather-card__meta">
              <div className="meta-item">
                <span className="meta-item__label">Rain probability</span>
                <span className="meta-item__value">
                  {rainProb != null ? `${rainProb}%` : '—'}
                </span>
              </div>
              <div className="meta-item">
                <span className="meta-item__label">Library impact</span>
                <span className="meta-item__value">
                  {impact?.impact_label || 'Low expected impact'}
                </span>
              </div>
              {weather?.apparent_temperature != null && (
                <div className="meta-item">
                  <span className="meta-item__label">Feels like</span>
                  <span className="meta-item__value">
                    {Math.round(weather.apparent_temperature)}°C
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        <details className="weather-tooltip">
          <summary>How weather is used</summary>
          <p>{TOOLTIP}</p>
        </details>
      </div>
    </section>
  )
}
