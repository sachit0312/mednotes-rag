import React, { useState } from 'react'

async function call(endpoint: string, payload: Record<string, unknown>) {
  const r = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!r.ok) {
    const t = await r.text()
    throw new Error(`${r.status} ${r.statusText}: ${t}`)
  }
  return r.json()
}

export default function App() {
  const [mode, setMode] = useState<'qa' | 'note'>('qa')
  const [text, setText] = useState('')
  const [extra, setExtra] = useState('')
  const [out, setOut] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)

  const run = async () => {
    if (!text.trim()) {
      alert('Please enter a question or topic.')
      return
    }
    setLoading(true)
    setStatus('Running…')
    setOut('')
    try {
      let res: any
      if (mode === 'qa') {
        res = await call('/api/qa', { q: text.trim(), extra: extra || undefined })
        setOut(res.answer || '')
      } else {
        res = await call('/api/note', { topic: text.trim(), extra: extra || undefined })
        setOut(res.card || '')
      }
      setStatus('Done')
    } catch (e) {
      console.error(e)
      setOut(String(e))
      setStatus('Error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="wrap">
      <h1>MedNotes RAG</h1>
      <p>Ask questions or generate a concise study note card from your ingested textbook.</p>

      <div className="card">
        <div className="row">
          <div>
            <label>Mode</label>
            <select value={mode} onChange={(e) => setMode(e.target.value as any)}>
              <option value="qa">Q&amp;A</option>
              <option value="note">Note Card</option>
            </select>
          </div>
          <div>
            <label>Topic / Question</label>
            <input
              type="text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="e.g., 'What determines mean arterial pressure?' or 'Renal autoregulation'"
            />
          </div>
        </div>

        <label>Advanced context (optional)</label>
        <textarea
          value={extra}
          onChange={(e) => setExtra(e.target.value)}
          placeholder="Optional: add extra hints or keywords. The retriever already expands prompts."
        />

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginTop: '12px' }}>
          <button disabled={loading} onClick={run}>{loading ? 'Running…' : 'Run'}</button>
          <span className="muted">{status}</span>
        </div>

        <div style={{ marginTop: '14px' }}>
          <div className="answer">{out || 'Output will appear here.'}</div>
        </div>
      </div>

      <div className="footer">
        Ensure Ollama is running and the index is built. Citations appear as [book:page-page].
      </div>
    </div>
  )
}

