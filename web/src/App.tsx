import React, { useState } from 'react'

const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || ''
const url = (path: string) => `${API_BASE}${path}`

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
  const [template, setTemplate] = useState<'general' | 'disease' | 'drug' | 'procedure'>('disease')
  const [stream, setStream] = useState(true)
  const [debug, setDebug] = useState(false)
  const [out, setOut] = useState('')
  const [loading, setLoading] = useState(false)
  const [contexts, setContexts] = useState<any[] | null>(null)

  async function callStream(endpoint: string, payload: Record<string, unknown>, onChunk: (s: string) => void) {
    const r = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!r.ok || !r.body) {
      const t = await r.text()
      throw new Error(`${r.status} ${r.statusText}: ${t}`)
    }
    const reader = r.body.getReader()
    const decoder = new TextDecoder()
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value, { stream: true })
      if (chunk) onChunk(chunk)
    }
  }

  const run = async () => {
    if (!text.trim()) {
      alert('Please enter a question or topic.')
      return
    }
    setLoading(true)
    setOut('')
    try {
      let res: any
      setContexts(null)
      if (stream) {
        const payload = mode === 'qa'
          ? { q: text.trim(), stream: true, extra: extra || undefined }
          : { topic: text.trim(), template, stream: true, extra: extra || undefined }
        await callStream(mode === 'qa' ? url('/api/qa') : url('/api/note'), payload, (chunk) => setOut(prev => prev + chunk))
      } else {
        if (mode === 'qa') {
          res = await call(url('/api/qa'), { q: text.trim(), extra: extra || undefined, debug })
          setOut(res.answer || '')
          setContexts(res.contexts || null)
        } else {
          res = await call(url('/api/note'), { topic: text.trim(), template, extra: extra || undefined, debug })
          setOut(res.card || '')
          setContexts(res.contexts || null)
        }
      }
    } catch (e) {
      console.error(e)
      setOut(String(e))
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
          {mode === 'note' && (
            <div>
              <label>Template</label>
              <select value={template} onChange={(e) => setTemplate(e.target.value as any)}>
                <option value="disease">disease</option>
                <option value="drug">Drug card</option>
                <option value="procedure">Procedure</option>
                <option value="general">General note</option>
              </select>
            </div>
          )}
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
          placeholder={mode === 'note'
            ? 'Optional: add hints (e.g., red flags, best test, cut-offs)'
            : 'Optional: add extra hints or keywords. The retriever already expands prompts.'}
        />

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginTop: '12px' }}>
          <button disabled={loading} onClick={run}>{loading ? 'Running…' : 'Run'}</button>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <input type="checkbox" checked={stream} onChange={(e) => setStream(e.target.checked)} />
            Stream
          </label>
          {!stream && (
            <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <input type="checkbox" checked={debug} onChange={(e) => setDebug(e.target.checked)} />
              Show retrieval debug
            </label>
          )}
        </div>

        <div style={{ marginTop: '14px' }}>
          <div className="answer">{out || 'Output will appear here.'}</div>
        </div>

        {contexts && contexts.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <label>Contexts (debug)</label>
            <div className="answer">
              {contexts.map((c, i) => (
                <div key={i} style={{ marginBottom: 6 }}>
                  [{c.book_id}:{c.page_start}-{c.page_end}] rrf={Number(c.score_rrf||0).toFixed(4)} xenc={Number(c.score_xenc||0).toFixed(4)} bm25={Number(c.score_bm25||0).toFixed(4)} dense={Number(1-(c.score_dense||0)).toFixed(4)} src:{c.dense?'D':''}{c.bm25?'B':''}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="footer">
        Ensure Ollama is running and the index is built. Citations appear as [book:page-page]. Disease/Drug/Procedure templates follow exam-first, compressed, retrieval-ready rules.
      </div>
    </div>
  )
}
