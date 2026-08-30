export default function ErrorState({ message, onRetry }) {
  return (
    <div className="error-state">
      <p className="error-state__message">{message}</p>
      {onRetry && (
        <button type="button" className="btn btn--secondary" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  )
}
