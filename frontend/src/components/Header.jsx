import { formatRelativeTime } from '../utils/helpers'

export default function Header({ health, lastUpdated }) {
  const online = health?.status === 'online'

  return (
    <header className="header">
      <div className="header__brand">
        <div className="header__logo" aria-hidden="true">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <rect x="2" y="6" width="24" height="18" rx="2" stroke="currentColor" strokeWidth="1.5" />
            <path d="M6 6V4.5C6 3.67 6.67 3 7.5 3H20.5C21.33 3 22 3.67 22 4.5V6" stroke="currentColor" strokeWidth="1.5" />
            <path d="M8 12H20M8 16H16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </div>
        <div>
          <h1 className="header__title">Smart Library Intelligence</h1>
          <p className="header__subtitle">AI-powered library occupancy prediction</p>
        </div>
      </div>
      <div className="header__status">
        <span className={`header__indicator ${online ? 'header__indicator--online' : 'header__indicator--offline'}`}>
          <span className="header__dot" />
          {online ? 'System Online' : 'System Offline'}
        </span>
        {lastUpdated && (
          <span className="header__updated">Last updated: {formatRelativeTime(lastUpdated)}</span>
        )}
      </div>
    </header>
  )
}
