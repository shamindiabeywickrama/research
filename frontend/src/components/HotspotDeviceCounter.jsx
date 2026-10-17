
import { useState } from 'react'

export default function HotspotDeviceCounter() {
  const [deviceCount, setDeviceCount] = useState(0)

  const decreaseCount = () => {
    setDeviceCount((count) => Math.max(0, count - 1))
  }

  const increaseCount = () => {
    setDeviceCount((count) => count + 1)
  }

  return (
    <section className="section">
      <div className="panel">
        <div className="section-header">
          <h2 className="section-title">Mobile Hotspot Device Count</h2>
          <span className="wifi-status-indicator" style={{ backgroundColor: '#10b981' }}>
            Manual Count
          </span>
        </div>

        <div className="panel__body">
          <p className="panel__muted">
            Record the connected-device count displayed on your phone's hotspot settings.
          </p>

          <div className="hotspot-counter">
            <button
              type="button"
              className="hotspot-counter__button"
              onClick={decreaseCount}
              disabled={deviceCount === 0}
              aria-label="Decrease connected device count"
            >
              −
            </button>

            <div className="hotspot-counter__value" aria-live="polite">
              {deviceCount}
              <span>connected devices</span>
            </div>

            <button
              type="button"
              className="hotspot-counter__button"
              onClick={increaseCount}
              aria-label="Increase connected device count"
            >
              +
            </button>
          </div>

          <p className="panel__muted">
            This count is manually recorded and is not used by the ML prediction model.
          </p>
        </div>
      </div>
    </section>
  )
}
