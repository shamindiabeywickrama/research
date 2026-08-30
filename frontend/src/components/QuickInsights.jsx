import LoadingState from './LoadingState'

const INSIGHTS = [
  {
    key: 'today_average',
    label: "Today's Average",
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M3 15L7 10L11 13L17 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M14 6H17V9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    suffix: ' students',
    isTime: false,
  },
  {
    key: 'today_peak',
    label: "Today's Peak",
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M10 3V17M10 3L6 7M10 3L14 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    suffix: ' students',
    isTime: false,
  },
  {
    key: 'quietest_period',
    label: 'Quietest Period',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <circle cx="10" cy="10" r="7" stroke="currentColor" strokeWidth="1.5" />
        <path d="M10 6V10L13 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
    suffix: '',
    isTime: true,
  },
  {
    key: 'available_seats',
    label: 'Available Seats',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <rect x="3" y="5" width="14" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
        <path d="M3 9H17" stroke="currentColor" strokeWidth="1.5" />
      </svg>
    ),
    suffix: '',
    isTime: false,
  },
]

export default function QuickInsights({ insights, loading, currentData }) {
  if (loading) {
    return (
      <section className="section">
        <div className="insights-grid">
          {[1, 2, 3, 4].map((i) => (
            <LoadingState key={i} variant="card-small" />
          ))}
        </div>
      </section>
    )
  }

  const data = {
    ...insights,
    available_seats: currentData?.available_seats ?? insights?.available_seats ?? 0,
  }

  return (
    <section className="section">
      <div className="insights-grid">
        {INSIGHTS.map(({ key, label, icon, suffix, isTime }) => (
          <div key={key} className="insight-card">
            <div className="insight-card__icon">{icon}</div>
            <div className="insight-card__content">
              <span className="insight-card__label">{label}</span>
              <span className="insight-card__value">
                {isTime ? data[key] : `${data[key] ?? '—'}${suffix}`}
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
