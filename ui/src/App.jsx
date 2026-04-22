import { useState, useEffect } from 'react'
import StatusBadge from './components/StatusBadge'
import MetricCard from './components/MetricCard'
import ReviewForm from './components/ReviewForm'

export default function App() {
  const [docs, setDocs] = useState([])
  const [expandedId, setExpandedId] = useState(null)
  const [expandedNoteId, setExpandedNoteId] = useState(null)
  const [form, setForm] = useState({})

  useEffect(() => {
    const fetchDocs = () =>
      fetch('/api/documents')
        .then(r => r.json())
        .then(setDocs)
    
    fetchDocs() // Auto re-load once every 10 seconds
    const interval = setInterval(fetchDocs, 10000) // time in ms
    return () => clearInterval(interval)
  }, [])

  const total     = docs.length
  const completed = docs.filter(d => d.status === 'completed').length
  const pending   = docs.filter(d => d.status === 'pending_review').length

  function openReview(doc) {
    setExpandedId(doc.id)
    setForm({
      doc_type:  doc.doc_type  ?? '',
      fund_name: doc.fund_name ?? '',
      amount:    doc.amount    ?? '',
      currency:  doc.currency  ?? '',
      due_date:  doc.due_date  ?? '',
    })
  }

  function submitReview(doc_id) {
    fetch(`/api/documents/${doc_id}/review`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...form, amount: form.amount ? parseFloat(form.amount) : null })
    })
      .then(r => r.json())
      .then(updated => {
        setDocs(docs.map(d => d.id === doc_id ? updated : d))
        setExpandedId(null)
      })
  }

  function discard(doc_id) {
    fetch(`/api/documents/${doc_id}/discard`, { method: 'POST' })
      .then(r => r.json())
      .then(() => setDocs(docs.filter(d => d.id !== doc_id)))
  }

  const th = { padding: '10px 12px', textAlign: 'left', fontSize: '0.75rem', fontWeight: 600, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }
  const td = { padding: '10px 12px', fontSize: '0.875rem' }

  return (
    <div style={{ minHeight: '100vh', background: '#f9fafb', fontFamily: 'system-ui, sans-serif' }}>

      <div style={{ background: '#1e3a5f', color: '#fff', padding: '1rem 2rem' }}>
        <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>AFO Agent</div>
        <div style={{ fontSize: '0.8rem', color: '#93c5fd', marginTop: '2px' }}>Automated Financial Document Processing</div>
      </div>

      <div style={{ padding: '2rem' }}>
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
          <MetricCard label="Total Documents" value={total}     color="#6366f1" />
          <MetricCard label="Completed"        value={completed} color="#10b981" />
          <MetricCard label="Pending Review"   value={pending}   color="#f59e0b" />
        </div>

        <div style={{ background: '#fff', borderRadius: '8px', border: '1px solid #e5e7eb', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f3f4f6', borderBottom: '1px solid #e5e7eb' }}>
                {['Filename','Status','Type','Fund','Amount','Currency','Due Date','Created','Notes','Actions'].map(h => (
                  <th key={h} style={th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {docs.map((doc, i) => (
                <>
                  <tr key={doc.id} style={{ background: i % 2 === 0 ? '#fff' : '#f9fafb', borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ ...td, maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.filename}</td>
                    <td style={td}><StatusBadge status={doc.status} /></td>
                    <td style={td}>{doc.doc_type ?? '—'}</td>
                    <td style={{ ...td, maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.fund_name ?? '—'}</td>
                    <td style={td}>{doc.amount ?? '—'}</td>
                    <td style={td}>{doc.currency ?? '—'}</td>
                    <td style={td}>{doc.due_date ?? '—'}</td>
                    <td style={{ ...td, whiteSpace: 'nowrap' }}>{new Date(doc.created_at).toLocaleString()}</td>
                    <td style={{ ...td, maxWidth: '220px', fontSize: '0.8rem', color: '#6b7280' }}>
                      {doc.error ? (
                        <>
                          {expandedNoteId === doc.id ? doc.error : doc.error.slice(0, 80) + (doc.error.length > 80 ? '...' : '')}
                          {doc.error.length > 80 && (
                            <span onClick={() => setExpandedNoteId(expandedNoteId === doc.id ? null : doc.id)}
                              style={{ color: '#6366f1', cursor: 'pointer', marginLeft: '4px' }}>
                              {expandedNoteId === doc.id ? 'less' : 'more'}
                            </span>
                          )}
                        </>
                      ) : '—'}
                    </td>
                    <td style={{ ...td, whiteSpace: 'nowrap' }}>
                      {doc.status === 'pending_review' && (
                        <>
                          <button onClick={() => openReview(doc)} style={{ background: '#6366f1', color: '#fff', border: 'none', borderRadius: '4px', padding: '4px 12px', cursor: 'pointer', fontSize: '0.8rem' }}>Review</button>
                          <button onClick={() => discard(doc.id)} style={{ background: '#fff', color: '#ef4444', border: '1px solid #ef4444', borderRadius: '4px', padding: '4px 12px', cursor: 'pointer', fontSize: '0.8rem', marginLeft: '6px' }}>Discard</button>
                        </>
                      )}
                    </td>
                  </tr>
                  {expandedId === doc.id && (
                    <ReviewForm
                      key={`${doc.id}-form`}
                      doc={doc}
                      form={form}
                      setForm={setForm}
                      onSubmit={() => submitReview(doc.id)}
                      onCancel={() => setExpandedId(null)}
                    />
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
