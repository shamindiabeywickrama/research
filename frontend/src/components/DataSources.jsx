const STATUS_STYLES = {
  Connected: 'source-status--connected',
  Active: 'source-status--connected',
  Demo: 'source-status--demo',
  Planned: 'source-status--planned',
}

const SOURCE_ICONS = {
  wifi: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M2 8C6.5 3.5 13.5 3.5 18 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M5 11C8 8 12 8 15 11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M8.5 14.5C9.3 13.7 10.7 13.7 11.5 14.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="10" cy="17" r="1" fill="currentColor" />
    </svg>
  ),
  calendar: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <rect x="3" y="4" width="14" height="13" rx="2" stroke="currentColor" strokeWidth="1.5" />
      <path d="M3 8H17M7 2V5M13 2V5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  ),
  exams: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M5 4H15V16H5V4Z" stroke="currentColor" strokeWidth="1.5" />
      <path d="M8 8H12M8 11H12M8 14H10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  ),
  weather: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M6 14H14C15.1 14 16 13.1 16 12C16 10.9 15.1 10 14 10C14 7.8 12.2 6 10 6C8.1 6 6.5 7.2 6 9C4.3 9 3 10.3 3 12C3 13.1 3.9 14 5 14H6Z" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  ),
  historical: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M4 16V6L10 3L16 6V16H4Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M8 10H12M8 13H12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  ),
}

export default function DataSources({ sources }) {
  if (!sources?.length) return null

  return (
    <section className="section">
      <div className="sources-section">
        <div className="section-header">
          <div>
            <h2 className="section-title">Prediction Data Sources</h2>
            <p className="section-subtitle">Inputs used by the occupancy prediction pipeline</p>
          </div>
        </div>

        <div className="sources-grid">
          {sources.map((source) => (
            <div key={source.id} className="source-card">
              <div className="source-card__icon">
                {SOURCE_ICONS[source.id] || SOURCE_ICONS.historical}
              </div>
              <div className="source-card__info">
                <span className="source-card__name">{source.name}</span>
                <span className="source-card__desc">{source.description}</span>
              </div>
              <span className={`source-status ${STATUS_STYLES[source.status] || ''}`}>
                {source.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
