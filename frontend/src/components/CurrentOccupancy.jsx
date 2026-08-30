import { formatRelativeTime, statusLabel, statusColor } from '../utils/helpers'
import LoadingState from './LoadingState'
import { isWifiMode } from '../utils/weather'

function OccupancyRing({ percentage, status }) {
  const radius = 72
  const circumference = 2 * Math.PI * radius
  const safePercent = Number.isFinite(percentage) ? Math.min(100, Math.max(0, percentage)) : 0
  const offset = circumference - (safePercent / 100) * circumference
  const color = statusColor(status)

  return (
    <div className="occupancy-ring">
      <svg width="180" height="180" viewBox="0 0 180 180">
        <circle
          cx="90"
          cy="90"
          r={radius}
          fill="none"
          stroke="var(--color-border)"
          strokeWidth="12"
        />
        <circle
          cx="90"
          cy="90"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 90 90)"
          className="occupancy-ring__progress"
        />
      </svg>
      <div className="occupancy-ring__center">
        <span className="occupancy-ring__percent">{safePercent.toFixed(1)}%</span>
      </div>
    </div>
  )
}

export default function CurrentOccupancy({ data, loading, dataMode }) {
  if (loading) {
    return (
      <section className="section">
        <LoadingState variant="card-large" />
      </section>
    )
  }

  if (!data) return null

  const isDemo = dataMode === 'demo' || dataMode === 'weather'
  const isWifi = isWifiMode(dataMode)

  return (
    <section className="section">
      {isDemo && (
        <div className="demo-badge">Demo Prediction Data</div>
      )}
      {isWifi && (
        <div className="wifi-badge">Wi-Fi Simulation Mode</div>
      )}
      <div className="occupancy-card">
        <div className="occupancy-card__header">
          <h2 className="section-title">Current Library Occupancy</h2>
        </div>
        <div className="occupancy-card__body">
          <div className="occupancy-card__ring">
            <OccupancyRing
              percentage={data.occupancy_percentage}
              status={data.status}
            />
          </div>
          <div className="occupancy-card__details">
            <div className="occupancy-card__count">
              <span className="occupancy-card__occupied">{data.occupied}</span>
              <span className="occupancy-card__separator">/</span>
              <span className="occupancy-card__capacity">{data.capacity}</span>
            </div>
            <p
              className="occupancy-card__status"
              style={{ color: statusColor(data.status) }}
            >
              {statusLabel(data.status)}
            </p>
            <div className="occupancy-card__meta">
              <div className="meta-item">
                <span className="meta-item__label">Available Seats</span>
                <span className="meta-item__value">{data.available_seats}</span>
              </div>
              <div className="meta-item">
                <span className="meta-item__label">Last Updated</span>
                <span className="meta-item__value">{formatRelativeTime(data.updated_at)}</span>
              </div>
              {isWifi && data.wifi_detected_devices !== undefined && (
                <div className="meta-item">
                  <span className="meta-item__label">Wi-Fi Devices</span>
                  <span className="meta-item__value">{data.wifi_detected_devices}</span>
                </div>
              )}
            </div>
            {data.message && (
              <p className="occupancy-card__note">{data.message}</p>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
