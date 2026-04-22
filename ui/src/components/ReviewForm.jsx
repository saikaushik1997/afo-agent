export default function ReviewForm({ doc, form, setForm, onSubmit, onCancel }) {
  return (
    <tr>
      <td colSpan="10" style={{ padding: '1.5rem', background: '#f0f4ff', borderBottom: '1px solid #e5e7eb' }}>
        <div style={{ display: 'flex', gap: '2rem' }}>
          <iframe
            src={`/api/documents/${doc.id}/file`}
            width="50%"
            height="500px"
            style={{ border: '1px solid #e5e7eb', borderRadius: '4px' }}
          />
          <div style={{ flex: 1 }}>
            {['doc_type', 'fund_name', 'amount', 'currency', 'due_date', 'human_reason'].map(field => (
              <div key={field} style={{ marginBottom: '0.75rem' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#374151', marginBottom: '4px', textTransform: 'uppercase' }}>{field}</label>
                <input
                  value={form[field]}
                  onChange={e => setForm({ ...form, [field]: e.target.value })}
                  style={{ width: '100%', padding: '6px 10px', border: '1px solid #d1d5db', borderRadius: '4px', fontSize: '0.875rem', boxSizing: 'border-box' }}
                />
              </div>
            ))}
            <button onClick={onSubmit} style={{ background: '#10b981', color: '#fff', border: 'none', borderRadius: '4px', padding: '6px 16px', cursor: 'pointer', fontWeight: 600 }}>Submit</button>
            <button onClick={onCancel} style={{ background: '#fff', color: '#6b7280', border: '1px solid #d1d5db', borderRadius: '4px', padding: '6px 16px', cursor: 'pointer', marginLeft: '8px' }}>Cancel</button>
          </div>
        </div>
      </td>
    </tr>
  )
}
