const STATUS_COLORS = {
  completed:      { bg: '#d1fae5', color: '#065f46' },
  pending_review: { bg: '#fef3c7', color: '#92400e' },
  processing:     { bg: '#dbeafe', color: '#1e40af' },
  received:       { bg: '#f3f4f6', color: '#374151' },
  discarded:      { bg: '#f3f4f6', color: '#9ca3af' },
  failed:         { bg: '#fee2e2', color: '#991b1b' },
}

export default function StatusBadge({ status }) {
  const s = STATUS_COLORS[status] || { bg: '#f3f4f6', color: '#374151' }
  return (
    <span style={{
      background: s.bg, color: s.color,
      padding: '2px 10px', borderRadius: '9999px',
      fontSize: '0.75rem', fontWeight: 600,
    }}>
      {status}
    </span>
  )
}
