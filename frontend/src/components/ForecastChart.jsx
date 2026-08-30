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

export default function ForecastChart({ forecast, capacity, loading, error, onRetry }) {
  const chartData = useMemo(() => {
    if (!forecast?.length) return null

    return {
      labels: forecast.map((f) => f.time),
      datasets: [
        {
          label: 'Predicted Occupancy',
          data: forecast.map((f) => f.predicted_occupancy),
          borderColor: '#2563EB',
          backgroundColor: 'rgba(37, 99, 235, 0.08)',
          fill: true,
          tension: 0.35,
          pointRadius: 3,
          pointHoverRadius: 5,
          borderWidth: 2,
        },
        {
          label: 'Library Capacity',
          data: forecast.map(() => capacity),
          borderColor: '#94A3B8',
          borderDash: [6, 4],
          pointRadius: 0,
          borderWidth: 1.5,
          fill: false,
        },
      ],
    }
  }, [forecast, capacity])

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
          label(context) {
            if (context.datasetIndex === 1) {
              return `Capacity: ${context.parsed.y}`
            }
            const item = forecast?.[context.dataIndex]
            if (!item) {
              return `Predicted: ${context.parsed.y}`
            }
            return [
              `Predicted: ${item.predicted_occupancy} students`,
              `Occupancy: ${item.percentage}%`,
              `Status: ${statusLabel(item.status)}`,
            ]
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
        suggestedMax: capacity,
        grid: { color: '#F1F5F9' },
        ticks: {
          font: { size: 11 },
          color: '#64748B',
        },
        title: {
          display: true,
          text: 'Number of people',
          color: '#64748B',
          font: { size: 12 },
        },
      },
    },
  }), [forecast, capacity])

  return (
    <section className="section">
      <div className="chart-section">
        <div className="section-header">
          <div>
            <h2 className="section-title">24-Hour Library Crowd Forecast</h2>
            <p className="section-subtitle">Predicted occupancy for the next 24 hours</p>
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
      </div>
    </section>
  )
}
