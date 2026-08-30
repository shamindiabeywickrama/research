import { statusLabel, statusColor, formatTime12h } from '../utils/helpers'

const PERIODS = [
  { label: 'Morning', hours: [8, 9, 10, 11] },
  { label: 'Afternoon', hours: [12, 13, 14, 15, 16] },
  { label: 'Evening', hours: [17, 18, 19] },
]

function getPeriodStatus(forecast, hours) {
  const slots = forecast.filter((f) => hours.includes(f.hour) && f.is_open)
  if (!slots.length) return { status: 'Closed', avg: 0 }

  const avg = slots.reduce((sum, s) => sum + s.percentage, 0) / slots.length
  let status = 'Low'
  if (avg >= 65) status = 'High'
  else if (avg >= 40) status = 'Moderate'
  return { status, avg: Math.round(avg) }
}

export default function CrowdTimeline({ forecast }) {
  if (!forecast?.length) return null

  const openSlots = forecast.filter((f) => f.is_open)
  const timelinePoints = openSlots.filter((_, i) => i % 2 === 0 || openSlots.length <= 6)

  return (
    <section className="section">
      <div className="timeline-section">
        <div className="section-header">
          <div>
            <h2 className="section-title">Today's Crowd Pattern</h2>
            <p className="section-subtitle">Expected crowd levels throughout the day</p>
          </div>
        </div>

        <div className="period-summary">
          {PERIODS.map(({ label, hours }) => {
            const { status } = getPeriodStatus(forecast, hours)
            return (
              <div key={label} className="period-card">
                <span className="period-card__label">{label}</span>
                <span
                  className="period-card__status"
                  style={{ color: statusColor(status) }}
                >
                  {statusLabel(status)}
                </span>
              </div>
            )
          })}
        </div>

        <div className="timeline-track">
          {timelinePoints.map((slot) => (
            <div key={slot.datetime} className="timeline-point">
              <span className="timeline-point__time">{formatTime12h(slot.time)}</span>
              <span
                className={`timeline-point__dot timeline-point__dot--${(slot.status || 'closed').toLowerCase()}`}
              />
              <span
                className="timeline-point__status"
                style={{ color: statusColor(slot.status) }}
              >
                {statusLabel(slot.status)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
