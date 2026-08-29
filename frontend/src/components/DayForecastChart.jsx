import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

function formatHour(h) {
  const period = h >= 12 ? 'PM' : 'AM'
  const hr12 = h % 12 === 0 ? 12 : h % 12
  return `${hr12}${period}`
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null
  const p = payload[0].payload
  return (
    <div className="spine-tooltip">
      {formatHour(label)} — {p.predicted_occupancy_percent}% ({p.predicted_occupancy_count} seats)
    </div>
  )
}

export default function DayForecastChart({ data }) {
  if (!data || data.length === 0) {
    return <div className="empty-state">No forecast yet — pick a date above and generate one.</div>
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} barCategoryGap={6}>
        <XAxis
          dataKey="hour"
          tickFormatter={formatHour}
          stroke="#5a6f63"
          tick={{ fontFamily: 'IBM Plex Mono', fontSize: 11, fill: '#9bb0a2' }}
          axisLine={{ stroke: '#33493f' }}
          tickLine={false}
        />
        <YAxis hide domain={[0, 100]} />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(201,162,39,0.08)' }} />
        <Bar dataKey="predicted_occupancy_percent" radius={[3, 3, 1, 1]} maxBarSize={26}>
          {data.map((entry, idx) => (
            <Cell
              key={idx}
              fill={entry.predicted_occupancy_percent >= 75 ? '#c05a3a' : entry.predicted_occupancy_percent >= 45 ? '#c9a227' : '#3f7a5c'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
