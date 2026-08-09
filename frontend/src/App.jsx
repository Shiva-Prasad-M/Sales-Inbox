import React, { useEffect, useState } from 'react'
import { generateSamples } from './sampleData'

const API = '/api'

export default function App() {
  const [emails, setEmails] = useState([])
  const [text, setText] = useState('')
  const [health, setHealth] = useState(null)
  const [dbHealth, setDbHealth] = useState(null)
  const [stats, setStats] = useState(null)
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(false)
  const [ingestTime, setIngestTime] = useState(null)
  const [error, setError] = useState(null)
  const [chat, setChat] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)

  async function get(path) {
    const r = await fetch(path)
    if (!r.ok) throw new Error('HTTP ' + r.status)
    return r.json()
  }

  async function refresh() {
    try {
      const [h, dh, st, tk] = await Promise.all([
        get('/health'), get('/health/database'), get('/api/stats'), get('/api/tasks')
      ])
      setHealth(h); setDbHealth(dh); setStats(st); setTasks(tk.tasks || [])
    } catch (e) {
      setError('Failed to load: ' + e.message)
    }
  }

  useEffect(() => { refresh() }, [])

  function handlePaste() {
    try {
      const parsed = JSON.parse(text)
      const arr = Array.isArray(parsed) ? parsed : (parsed.emails || [])
      if (!Array.isArray(arr)) throw new Error('Expected an array of emails or {emails:[...]}')
      setEmails(arr)
      setError(null)
    } catch (e) {
      setError('Invalid JSON: ' + e.message)
    }
  }

  function handleFile(e) {
    const file = e.target.files[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      try {
        const parsed = JSON.parse(reader.result)
        const arr = Array.isArray(parsed) ? parsed : (parsed.emails || [])
        setEmails(arr)
        setError(null)
      } catch (err) {
        setError('Invalid file JSON: ' + err.message)
      }
    }
    reader.readAsText(file)
  }

  function handleGenerate() {
    setEmails(generateSamples(250))
    setError(null)
  }

  async function handleIngest() {
    if (!emails.length) { setError('No emails to ingest'); return }
    setLoading(true); setError(null)
    const t0 = Date.now()
    try {
      const r = await fetch('/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ emails })
      })
      const data = await r.json()
      if (!r.ok) throw new Error(JSON.stringify(data))
      setIngestTime({ ms: Date.now() - t0, ...data })
      await refresh()
    } catch (e) {
      setError('Ingest failed: ' + e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleChat(e) {
    e.preventDefault()
    if (!chatInput.trim()) return
    const q = chatInput
    setChat(c => [...c, { role: 'user', text: q }])
    setChatInput(''); setChatLoading(true)
    try {
      const r = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q })
      })
      const data = await r.json()
      setChat(c => [...c, { role: 'bot', text: data.answer, data: data.supporting_data }])
    } catch (err) {
      setChat(c => [...c, { role: 'bot', text: 'Error: ' + err.message }])
    } finally {
      setChatLoading(false)
    }
  }

  return (
    <div className="app">
      <header>
        <h1>📥 Alumnx Sales Inbox</h1>
        <div className="status">
          {dbHealth?.status === 'healthy' ? '🟢 DB connected' : `🔴 ${dbHealth?.error || 'DB down'}`}
        </div>
      </header>

      <div className="card">
        <h2>1. Input / Paste Emails</h2>
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder='Paste JSON here, e.g. [{"email_id":"e1","subject":"...","body":"...","from_name":"...","from_email":"...","thread_id":"...","received_at":"...","is_reply":false}]'
        />
        <div className="row" style={{ marginTop: 12 }}>
          <button className="btn" onClick={handlePaste}>Parse JSON</button>
          <button className="btn secondary" onClick={handleGenerate}>Generate 250 samples</button>
          <label className="btn secondary" style={{ display: 'inline-block', cursor: 'pointer' }}>
            Upload file
            <input type="file" accept=".json" style={{ display: 'none' }} onChange={handleFile} />
          </label>
          {emails.length > 0 && (
            <button className="btn" onClick={handleIngest} disabled={loading}>
              {loading ? 'Ingesting...' : `Ingest ${emails.length} emails`}
            </button>
          )}
        </div>
        {error && <div className="error">{error}</div>}
        {ingestTime && (
          <div className="success">
            ✓ Processed {ingestTime.processed}, created {ingestTime.tasks_created}, updated {ingestTime.tasks_updated}, skipped {ingestTime.skipped}
            {ingestTime.errors?.length ? `, errors: ${ingestTime.errors.join('; ')}` : ''} in {ingestTime.ms}ms
          </div>
        )}
      </div>

      <div className="card">
        <h2>2. Raw Email Table <span className="muted">({emails.length} emails)</span></h2>
        {emails.length > 0 ? (
          <div style={{ maxHeight: 300, overflowY: 'auto' }}>
            <table>
              <thead>
                <tr><th>ID</th><th>From</th><th>Subject</th><th>Thread</th></tr>
              </thead>
              <tbody>
                {emails.slice(0, 50).map((e, i) => (
                  <tr key={i}>
                    <td>{e.email_id}</td>
                    <td>{e.from_name}</td>
                    <td>{e.subject}</td>
                    <td>{e.thread_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <div className="muted">No emails loaded yet.</div>}
      </div>

      <div className="card">
        <h2>3. Live Tasks & Stats</h2>
        {stats ? (
          <div className="grid">
            <div className="stat"><div className="num">{stats.processed}</div><div className="label">Emails processed</div></div>
            <div className="stat"><div className="num">{stats.created}</div><div className="label">Tasks created</div></div>
            <div className="stat"><div className="num">{stats.updated}</div><div className="label">Tasks updated</div></div>
            <div className="stat"><div className="num">{stats.skipped}</div><div className="label">Skipped</div></div>
            <div className="stat"><div className="num">₹{(stats.total_open_rfp_value || 0).toLocaleString('en-IN')}</div><div className="label">Open RFP value</div></div>
          </div>
        ) : <div className="muted">Loading stats...</div>}

        <h2 style={{ marginTop: 20 }}>Tasks</h2>
        <div style={{ maxHeight: 400, overflowY: 'auto' }}>
          <table>
            <thead>
              <tr><th>Task ID</th><th>Title</th><th>Assignee</th><th>Category</th><th>Priority</th><th>Value</th><th>Confidence</th></tr>
            </thead>
            <tbody>
              {tasks.map(t => (
                <tr key={t.task_id}>
                  <td>{t.task_id}</td>
                  <td>{t.title}</td>
                  <td>{t.assignee_id}</td>
                  <td><span className={`badge ${t.category}`}>{t.category}</span></td>
                  <td>{t.priority}</td>
                  <td>{t.deal_value_inr ? '₹' + t.deal_value_inr.toLocaleString('en-IN') : '—'}</td>
                  <td>{(t.confidence * 100).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h2>4. Grounded Chat</h2>
        <div className="chat">
          <div className="chat-msgs">
            {chat.length === 0 && <div className="muted">Ask questions about the ingested data, e.g. "How many enterprise RFPs?", "Show everything in triage and why".</div>}
            {chat.map((m, i) => (
              <div key={i} className={`chat-msg ${m.role}`}>
                <div className="bubble">
                  {m.text}
                  {m.data && <div className="muted" style={{ marginTop: 6 }}>data: {JSON.stringify(m.data)}</div>}
                </div>
              </div>
            ))}
            {chatLoading && <div className="chat-msg bot"><div className="bubble"><span className="spinner" /> thinking...</div></div>}
          </div>
          <form className="chat-input" onSubmit={handleChat}>
            <input type="text" value={chatInput} onChange={e => setChatInput(e.target.value)} placeholder="Ask a question..." />
            <button className="btn" disabled={chatLoading}>Ask</button>
          </form>
        </div>
      </div>
    </div>
  )
}
