import { useEffect, useState } from 'react'
import { getNetworkStatus, connectNetworkWebSocket } from '../api'
import { formatRelativeTime } from '../utils/helpers'

export default function WiFiStatus({ dataMode }) {
  const [networkStatus, setNetworkStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [wsConnected, setWsConnected] = useState(false)

  useEffect(() => {
    if (dataMode !== 'wifi') {
      setLoading(false)
      return
    }

    // Initial fetch
    loadNetworkStatus()

    // Set up WebSocket for real-time updates
    const ws = connectNetworkWebSocket(
      (data) => {
        setNetworkStatus(data)
        setWsConnected(true)
        setLoading(false)
      },
      (error) => {
        console.error('WebSocket error:', error)
        setWsConnected(false)
      }
    )

    // Poll as fallback
    const interval = setInterval(loadNetworkStatus, 3000)

    return () => {
      clearInterval(interval)
      if (ws) ws.close()
    }
  }, [dataMode])

  const loadNetworkStatus = async () => {
    try {
      const status = await getNetworkStatus()
      setNetworkStatus(status)
      setLoading(false)
    } catch (error) {
      console.error('Failed to load network status:', error)
      setLoading(false)
    }
  }

  if (dataMode !== 'wifi') {
    return null
  }

  if (loading) {
    return (
      <section className="section">
        <div className="panel">
          <div className="section-header">
            <h2 className="section-title">Local Wi-Fi Simulation</h2>
          </div>
          <p className="panel__muted">Loading network status...</p>
        </div>
      </section>
    )
  }

  if (!networkStatus || !networkStatus.enabled) {
    return (
      <section className="section">
        <div className="panel">
          <div className="section-header">
            <h2 className="section-title">Local Wi-Fi Simulation</h2>
          </div>
          <p className="panel__muted">Wi-Fi simulation is not enabled.</p>
        </div>
      </section>
    )
  }

  const statusColor = networkStatus.status === 'active' ? '#10b981' : '#ef4444'
  const lastScanTime = networkStatus.last_scan ? formatRelativeTime(networkStatus.last_scan) : 'Never'

  return (
    <section className="section">
      <div className="wifi-simulation-badge">Simulation Mode</div>
      <div className="panel">
        <div className="section-header">
          <h2 className="section-title">Local Wi-Fi Simulation</h2>
          <div className="wifi-status-indicator" style={{ backgroundColor: statusColor }}>
            {wsConnected ? '● Live' : '● Monitoring'}
          </div>
        </div>
        <div className="panel__body">
          <div className="wifi-status-grid">
            <div className="wifi-status-item">
              <span className="wifi-status-item__label">Network</span>
              <span className="wifi-status-item__value">{networkStatus.network}</span>
            </div>
            <div className="wifi-status-item">
              <span className="wifi-status-item__label">Detected Devices</span>
              <span className="wifi-status-item__value wifi-status-item__value--highlight">
                {networkStatus.detected_devices}
              </span>
            </div>
            <div className="wifi-status-item">
              <span className="wifi-status-item__label">Status</span>
              <span className="wifi-status-item__value" style={{ color: statusColor }}>
                {networkStatus.status === 'active' ? 'Active' : 'Inactive'}
              </span>
            </div>
            <div className="wifi-status-item">
              <span className="wifi-status-item__label">Last Scan</span>
              <span className="wifi-status-item__value">{lastScanTime}</span>
            </div>
          </div>
          {networkStatus.baseline > 0 && (
            <div className="wifi-baseline-note">
              Baseline occupancy: +{networkStatus.baseline}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
