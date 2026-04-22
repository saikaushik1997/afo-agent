export default function MetricCard({ label, value, color, onClick, active }) {
  return (
    <div onClick={onClick} style={{
      background: active ? color : '#fff',
      border: `2px solid ${color}`,
      borderTop: `3px solid ${color}`, borderRadius: '8px',
      padding: '1.25rem 1.5rem', minWidth: '150px',
      cursor: 'pointer',
    }}>
      <div style={{ fontSize: '2rem', fontWeight: 700, color: active ? '#fff' : color }}>{value}</div>
      <div style={{ fontSize: '0.85rem', color: active ? '#fff' : '#6b7280', marginTop: '4px' }}>{label}</div>
    </div>
  )
}
