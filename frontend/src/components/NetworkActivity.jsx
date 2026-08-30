import { useEffect, useState } from 'react'
import { getNetworkEvents } from '../api'
import { formatRelativeTime } from '../utils/helpers'

import { isWifiMode } from '../utils/weather'

export default function NetworkActivity({ dataMode }) {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!isWifiMode(dataMode)) {
      setLoading(false)
      return
    }

    loadEvents()
    const interval = setInterval(loadEvents, 3000)

    return () => clearInterval(interval)
  }, [dataMode])

  const loadEvents = async () => {
    try {
      const data = await getNetworkEvents()
      setEvents(data.events || [])
      setLoading(false)
    } catch (error) {
      console.error('Failed to load network events:', error)
      setLoading(false)
    }
  }

  if (!isWifiMode(dataMode)) {
    return null
  }

  if (loading) {
    return (
      <section className="section">
        <div className="panel">
          <div className="section-header">
            <h2 className="section-title">Live Network Activity</h2>
          </div>
          <p className="panel__muted">Loading activity...</p>
        </div>
      </section>
    )
  }

  if (events.length === 0) {
    return (
      <section className="section">
        <div className="panel">
          <div className="section-header">
            <h2 className="section-title">Live Network Activity</h2>
          </div>
          <p className="network-activity-empty">No recent device activity</p>
        </div>
      </section>
    )
  }

  return (
    <section className="section">
      <div className="panel">
        <div className="section-header">
          <h2 className="section-title">Live Network Activity</h2>
        </div>
        <div className="panel__body">
          <div className="network-activity-list">
            {events.slice().reverse().map((event, index) => (
              <div key={index} className="network-activity-item">
                <div className="network-activity-item__icon">
                  {event.event === 'DEVICE_CONNECTED' ? (
                    <span className="network-activity-icon network-activity-icon--connected">●</span>
                  ) : (
                    <span className="network-activity-icon network-activity-icon--disconnected">●</span>
                  )}
                </div>
                <div className="network-activity-item__content">
                  <div className="network-activity-item__event">
                    {event.event === 'DEVICE_CONNECTED' ? 'Device connected' : 'Device disconnected'}
                  </div>
                  <div className="network-activity-item__detail">
                    {event.count_change > 0 ? `+${event.count_change} device detected` : `${event.count_change} device detected`}
                  </div>
                </div>
                <div className="network-activity-item__time">
                  {formatRelativeTime(event.timestamp)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
