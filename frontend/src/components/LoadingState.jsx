export default function LoadingState({ variant = 'card' }) {
  if (variant === 'chart') {
    return (
      <div className="skeleton skeleton--chart" aria-label="Loading chart">
        <div className="skeleton__bars">
          {[...Array(12)].map((_, i) => (
            <div key={i} className="skeleton__bar" style={{ height: `${30 + (i % 5) * 12}%` }} />
          ))}
        </div>
      </div>
    )
  }

  if (variant === 'card-large') {
    return <div className="skeleton skeleton--card-large" aria-label="Loading" />
  }

  if (variant === 'card-medium') {
    return <div className="skeleton skeleton--card-medium" aria-label="Loading" />
  }

  if (variant === 'card-small') {
    return <div className="skeleton skeleton--card-small" aria-label="Loading" />
  }

  return <div className="skeleton skeleton--card" aria-label="Loading" />
}
