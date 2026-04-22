export default function MetricCard({ label, value, color }) {
  return (
    <div style={{
      background: '#fff', border: '1px solid #e5e7eb',
      borderTop: `3px solid ${color}`, borderRadius: '8px',
      padding: '1.25rem 1.5rem', minWidth: '150px',
    }}>
      <div style={{ fontSize: '2rem', fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: '0.85rem', color: '#6b7280', marginTop: '4px' }}>{label}</div>
    </div>
  )
}
