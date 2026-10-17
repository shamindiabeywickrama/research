import { useMemo } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Line } from 'react-chartjs-2'
import LoadingState from './LoadingState'
import ErrorState from './ErrorState'
import { statusLabel } from '../utils/helpers'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
)

export default function ForecastChart({
  forecast,
  capacity,
  loading,
  error,
  onRetry,
  weatherAdjusted,
  adjustmentNote,
  aggregation,
  period = '24h',
  valueMode = 'count',
  intervalHours = 1,
}) {
  const showAdjusted = Boolean(weatherAdjusted)
  const isDaily = period === '7d'
  const isPercentage = valueMode === 'percentage'
  const displayedForecast = useMemo(() => {
    if (!forecast?.length || isDaily || intervalHours <= 1) return forecast
    return forecast.filter((_, index) => index % intervalHours === 0)
  }, [forecast, intervalHours, isDaily])

  const chartData = useMemo(() => {
    if (!displayedForecast?.length) return null

    if (isPercentage) {
      const datasets = []
      if (showAdjusted) {
        datasets.push({
          label: 'Random Forest forecast (%)',
          data: displayedForecast.map((item) =>
            isDaily ? item.base_average_occupancy_percentage : item.base_percentage,
          ),
          borderColor: '#94A3B8',
          backgroundColor: 'transparent',
          fill: false,
          tension: 0.35,
          pointRadius: 2,
          pointHoverRadius: 4,
          borderWidth: 1.5,
          borderDash: [4, 3],
        })
        datasets.push({
          label: 'Weather-adjusted estimate (%)',
          data: displayedForecast.map((item) =>
            isDaily ? item.average_occupancy_percentage : item.percentage,
          ),
          borderColor: '#2563EB',
          backgroundColor: 'rgba(37, 99, 235, 0.08)',
          fill: true,
          tension: 0.35,
          pointRadius: 3,
          pointHoverRadius: 5,
          borderWidth: 2,
        })
      } else {
        datasets.push({
          label: isDaily ? 'Daily average occupancy (%)' : 'Predicted occupancy (%)',
          data: displayedForecast.map((item) =>
            isDaily ? item.average_occupancy_percentage : item.percentage,
          ),
          borderColor: '#2563EB',
          backgroundColor: 'rgba(37, 99, 235, 0.08)',
          fill: true,
          tension: 0.35,
          pointRadius: 3,
          pointHoverRadius: 5,
          borderWidth: 2,
        })
      }

      return {
        labels: displayedForecast.map((item) => item.time),
        datasets,
      }
    }

    const datasets = []

    if (showAdjusted) {
      datasets.push({
        label: 'ML Forecast',
        data: displayedForecast.map((f) => f.base_prediction ?? f.predicted_occupancy),
        borderColor: '#94A3B8',
        backgroundColor: 'transparent',
        fill: false,
        tension: 0.35,
        pointRadius: 2,
        pointHoverRadius: 4,
        borderWidth: 1.5,
        borderDash: [4, 3],
      })
      datasets.push({
        label: 'Weather-adjusted estimate',
        data: displayedForecast.map((f) => f.predicted_occupancy),
        borderColor: '#2563EB',
        backgroundColor: 'rgba(37, 99, 235, 0.08)',
        fill: true,
        tension: 0.35,
        pointRadius: 3,
        pointHoverRadius: 5,
        borderWidth: 2,
      })
    } else {
      datasets.push({
        label: 'Predicted Occupancy',
        data: displayedForecast.map((f) => f.predicted_occupancy),
        borderColor: '#2563EB',
        backgroundColor: 'rgba(37, 99, 235, 0.08)',
        fill: true,
        tension: 0.35,
        pointRadius: 3,
        pointHoverRadius: 5,
        borderWidth: 2,
      })
    }

    datasets.push({
      label: 'Library Capacity',
      data: displayedForecast.map(() => capacity),
      borderColor: '#94A3B8',
      borderDash: [6, 4],
      pointRadius: 0,
      borderWidth: 1.5,
      fill: false,
    })

    return {
      labels: displayedForecast.map((f) => f.time),
      datasets,
    }
  }, [displayedForecast, capacity, showAdjusted, isDaily, isPercentage])

  const options = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: {
        position: 'top',
        align: 'end',
        labels: {
          boxWidth: 12,
          boxHeight: 12,
          usePointStyle: true,
          font: { family: 'Inter, sans-serif', size: 12 },
          color: '#64748B',
        },
      },
      tooltip: {
        backgroundColor: '#FFFFFF',
        titleColor: '#0F172A',
        bodyColor: '#64748B',
        borderColor: '#E2E8F0',
        borderWidth: 1,
        padding: 12,
        boxPadding: 4,
        callbacks: {
          title(items) {
            const item = displayedForecast?.[items[0]?.dataIndex]
            if (!item) return ''
            return isDaily ? `${item.date} (local date)` : item.datetime
          },
          label(context) {
            const item = displayedForecast?.[context.dataIndex]
            const label = context.dataset.label
            if (isPercentage) {
              if (!item) return `${label}: ${context.parsed.y}%`
              if (isDaily) {
                return [
                  `${label}: ${context.parsed.y}%`,
                  `Future open hours included: ${item.hours_included}`,
                ]
              }
              return `${label}: ${context.parsed.y}%`
            }
            if (label === 'Library Capacity') {
              return `Capacity: ${context.parsed.y}`
            }
            if (!item) {
              return `${label}: ${context.parsed.y}`
            }
            const lines = []
            if (label === 'ML Forecast') {
              lines.push(`ML Forecast: ${item.base_prediction ?? item.predicted_occupancy} students`)
            } else {
              lines.push(`Weather-adjusted: ${item.predicted_occupancy} students`)
              if (item.base_prediction != null && item.base_prediction !== item.predicted_occupancy) {
                lines.push(`ML Forecast: ${item.base_prediction} students`)
              }
            }
            if (item.weather?.condition) {
              lines.push(`Weather: ${item.weather.condition}`)
            }
            lines.push(`Occupancy: ${item.percentage}%`)
            lines.push(`Status: ${statusLabel(item.status)}`)
            return lines
          },
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: {
          maxRotation: 45,
          minRotation: 0,
          autoSkip: true,
          maxTicksLimit: 12,
          font: { size: 11 },
          color: '#64748B',
        },
      },
      y: {
        beginAtZero: true,
        min: isPercentage ? 0 : undefined,
        max: isPercentage ? 100 : undefined,
        suggestedMax: isPercentage ? undefined : capacity,
        grid: { color: '#F1F5F9' },
        ticks: {
          font: { size: 11 },
          color: '#64748B',
          stepSize: isPercentage ? 20 : undefined,
        },
        title: {
          display: true,
          text: isPercentage ? 'Occupancy (%)' : 'Number of people',
          color: '#64748B',
          font: { size: 12 },
        },
      },
    },
  }), [displayedForecast, capacity, isDaily, isPercentage])

  const chartTitle = isPercentage
    ? isDaily ? '7-Day Daily Average Occupancy' : 'Next 24 Hours: Hourly Occupancy'
    : '24-Hour Library Crowd Forecast'
  const chartSubtitle = isPercentage
    ? isDaily
      ? aggregation || 'Daily average of future open-hour occupancy predictions.'
      : intervalHours > 1
        ? `Predicted occupancy every ${intervalHours} hours.`
        : 'Predicted occupancy for each upcoming hour.'
    : showAdjusted
      ? 'Base ML prediction and weather-adjusted estimate'
      : 'Predicted occupancy for the next 24 hours'

  return (
    <section className="section">
      <div className="chart-section">
        <div className="section-header">
          <div>
            <h2 className="section-title">{chartTitle}</h2>
            <p className="section-subtitle">{chartSubtitle}</p>
          </div>
          <div className="legend-pills">
            <span className="legend-pill legend-pill--low">Low</span>
            <span className="legend-pill legend-pill--medium">Moderate</span>
            <span className="legend-pill legend-pill--high">High</span>
          </div>
        </div>

        <div className="chart-container">
          {loading && <LoadingState variant="chart" />}
          {error && !loading && (
            <ErrorState message="Unable to load forecast data." onRetry={onRetry} />
          )}
          {!loading && !error && (!forecast || forecast.length === 0) && (
            <div className="empty-state">No forecast data available.</div>
          )}
          {!loading && !error && chartData && (
            <Line data={chartData} options={options} />
          )}
        </div>
        {showAdjusted && adjustmentNote && (
          <p className="weather-chart-note">{adjustmentNote}</p>
        )}
      </div>
    </section>
  )
}
