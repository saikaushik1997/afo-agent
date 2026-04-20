import { useState, useEffect } from 'react'

export default function App() {
  const [docs, setDocs] = useState([])
  const [expandedId, setExpandedId] = useState(null)
  const [form, setForm] = useState({})

  useEffect(() => {
    fetch('/api/documents')
      .then(r => r.json())
      .then(setDocs)
  }, [])

  function openReview(doc) {
    setExpandedId(doc.id)
    setForm({
      doc_type: doc.doc_type ?? '',
      fund_name: doc.fund_name ?? '',
      amount: doc.amount ?? '',
      currency: doc.currency ?? '',
      due_date: doc.due_date ?? ''
    })
  }

  function submitReview(doc_id) {
    fetch(`/api/documents/${doc_id}/review`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...form,
        amount: form.amount ? parseFloat(form.amount) : null
      })
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
      .then(() => {
        setDocs(docs.filter(d => d.id !== doc_id))
      })
  }

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>AFO Agent</h1>
      <table border="1" cellPadding="8" style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead>
          <tr>
            <th>Filename</th>
            <th>Status</th>
            <th>Type</th>
            <th>Fund</th>
            <th>Amount</th>
            <th>Currency</th>
            <th>Due Date</th>
            <th>Created</th>
            <th>Notes</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {docs.map(doc => (
            <>
              <tr key={doc.id}>
                <td>{doc.filename}</td>
                <td>{doc.status}</td>
                <td>{doc.doc_type ?? '—'}</td>
                <td>{doc.fund_name ?? '—'}</td>
                <td>{doc.amount ?? '—'}</td>
                <td>{doc.currency ?? '—'}</td>
                <td>{doc.due_date ?? '—'}</td>
                <td>{new Date(doc.created_at).toLocaleString()}</td>
                <td style={{ maxWidth: '300px', fontSize: '0.85em', color: '#666' }}>{doc.error ?? '—'}</td>
                <td>
                  {doc.status === 'pending_review' && (
                    <>
                      <button onClick={() => openReview(doc)}>Review</button>
                      <button onClick={() => discard(doc.id)} style={{ marginLeft: '8px' }}>Discard</button>
                    </>
                  )}
                </td>
              </tr>
              {expandedId === doc.id && (
                <tr key={`${doc.id}-form`}>
                  <td colSpan="9">
                    <div style={{ display: 'flex', gap: '2rem' }}>
                      <iframe
                        src={`/api/documents/${doc.id}/file`}
                        width="50%"
                        height="500px"
                        style={{ border: '1px solid #ccc' }}
                      />
                      <div style={{ flex: 1 }}>
                        {['doc_type', 'fund_name', 'amount', 'currency', 'due_date'].map(field => (
                          <div key={field} style={{ marginBottom: '0.5rem' }}>
                            <label>{field}: </label>
                            <input
                              value={form[field]}
                              onChange={e => setForm({ ...form, [field]: e.target.value })}
                            />
                          </div>
                        ))}
                        <button onClick={() => submitReview(doc.id)}>Submit</button>
                        <button onClick={() => setExpandedId(null)} style={{ marginLeft: '8px' }}>Cancel</button>
                      </div>
                    </div>
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>
    </div>
  )
}
