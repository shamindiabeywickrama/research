import { weatherIcon } from '../utils/weather'
import { formatTime12h } from '../utils/helpers'

export default function WeatherTimeline({ forecast }) {
  if (!forecast?.length) return null

  const points = forecast.filter((slot) => slot.weather).filter((_, index) => index % 3 === 0)

  if (!points.length) return null

  return (
    <section className="section">
      <div className="weather-timeline">
        <div className="section-header">
          <div>
            <h2 className="section-title">Weather Timeline</h2>
            <p className="section-subtitle">Hourly context for the occupancy forecast</p>
          </div>
        </div>
        <div className="weather-timeline__track">
          {points.map((slot) => {
            const wx = slot.weather
            return (
              <div key={slot.datetime} className="weather-timeline__item">
                <span className="weather-timeline__time">{formatTime12h(slot.time)}</span>
                <span className="weather-timeline__icon" aria-hidden="true">
                  {weatherIcon(wx.condition)}
                </span>
                <span className="weather-timeline__temp">
                  {wx.temperature != null ? `${Math.round(wx.temperature)}°C` : '—'}
                </span>
                <span className="weather-timeline__rain">
                  {wx.rain_probability != null ? `${wx.rain_probability}%` : '—'}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
