import { NavLink } from 'react-router-dom'

const links = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/predictions', label: 'Crowd Predictions' },
  { to: '/study-planner', label: 'Study Planner' },
  { to: '/weather', label: 'Weather' },
  { to: '/model-evaluation', label: 'Model Evaluation' },
]

export default function Navigation() {
  return (
    <nav className="navigation" aria-label="Main navigation">
      {links.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          end={link.to === '/dashboard'}
          className={({ isActive }) =>
            `navigation__link${isActive ? ' navigation__link--active' : ''}`
          }
        >
          {link.label}
        </NavLink>
      ))}
    </nav>
  )
}