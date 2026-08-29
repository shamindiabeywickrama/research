export default function HistoryTable({ rows }) {
  if (!rows || rows.length === 0) {
    return <div className="empty-state">No prediction history yet. Once Supabase is connected, every prediction you generate will appear here.</div>
  }

  return (
    <table className="history-table">
      <thead>
        <tr>
          <th>Date</th>
          <th>Hour</th>
          <th>Predicted %</th>
          <th>Seats</th>
          <th>Context</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.id}>
            <td>{r.date}</td>
            <td>{String(r.hour).padStart(2, '0')}:00</td>
            <td>{r.predicted_occupancy_percent}%</td>
            <td>{r.predicted_occupancy_count}</td>
            <td>
              {r.is_exam_period ? 'Exam period' : r.is_semester_break ? 'Semester break' : r.is_weekend ? 'Weekend' : 'Regular day'}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
