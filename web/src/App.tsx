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
  const [apiOk, setApiOk] = useState<boolean | null>(null)
  const [ollamaInfo, setOllamaInfo] = useState<{ base: string; version: any; current_model: string } | null>(null)
  const [models, setModels] = useState<string[]>([])
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [pending, setPending] = useState<string>('')
  const [adminKey, setAdminKey] = useState<string>('')
  const [checkingApi, setCheckingApi] = useState(false)
  const [checkingOllama, setCheckingOllama] = useState(false)
  const [restartingApi, setRestartingApi] = useState(false)
  const [restartingOllama, setRestartingOllama] = useState(false)
  const [switchingModel, setSwitchingModel] = useState(false)
  const [adminError, setAdminError] = useState<string>('')
  const [toasts, setToasts] = useState<{ id: number; text: string; type: 'success'|'error'|'info' }[]>([])
  const [apiError, setApiError] = useState<string>('')
  const [ollamaError, setOllamaError] = useState<string>('')
  const [modelError, setModelError] = useState<string>('')

  function pushToast(text: string, type: 'success'|'error'|'info' = 'info', ttl = 2500) {
    const id = Date.now() + Math.floor(Math.random() * 1000)
    setToasts(prev => [...prev, { id, text, type }])
    window.setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, ttl)
  }
  const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || ''

  React.useEffect(() => {
    const k = localStorage.getItem('adminKey') || 'sachit loves astha'
    setAdminKey(k)
    if (!localStorage.getItem('adminKey')) localStorage.setItem('adminKey', k)
    // initial checks
    checkApi()
    checkOllama()
    const id = setInterval(() => {
      checkApi()
      checkOllama()
    }, 30000)
    return () => clearInterval(id)
  }, [])

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

  // System helpers
  const checkApi = async () => {
    try {
      setCheckingApi(true)
      const r = await fetch(url('/api/health'))
      setApiOk(r.ok)
      setApiError(r.ok ? '' : 'API unreachable')
    } catch {
      setApiOk(false)
      setApiError('API unreachable')
    } finally {
      setCheckingApi(false)
    }
  }

  const checkOllama = async () => {
    try {
      setCheckingOllama(true)
      const r = await fetch(url('/api/ollama/health'))
      if (!r.ok) throw new Error()
      const d = await r.json()
      setOllamaInfo(d)
      if (!selectedModel) setSelectedModel(d.current_model || '')
      const rr = await fetch(url('/api/ollama/models'))
      if (rr.ok) {
        const mm = await rr.json()
        setModels(mm.models || [])
        setModelError('')
      }
      setOllamaError('')
    } catch {
      setOllamaInfo(null)
      setModels([])
      setOllamaError('Ollama unreachable')
      setModelError('')
    } finally {
      setCheckingOllama(false)
    }
  }

  const restartApi = async () => {
    try {
      setRestartingApi(true)
      setPending('Restarting API...')
      const headers: any = { }
      if (adminKey) headers['X-Admin-Key'] = adminKey
      const r = await fetch(url('/api/admin/restart_api'), { method: 'POST', headers })
      if (!r.ok) {
        const t = await r.text()
        setAdminError(r.status === 403 ? 'Invalid admin key' : `Admin error: ${r.status}`)
        throw new Error(t)
      }
      setAdminError('')
      pushToast('API restart triggered', 'success')
    } catch (e) {
      pushToast('Failed to restart API', 'error')
    } finally {
      setTimeout(() => checkApi(), 1500)
      setPending('')
      setRestartingApi(false)
    }
  }

  const restartOllama = async () => {
    try {
      setRestartingOllama(true)
      setPending('Restarting Ollama...')
      const headers: any = { }
      if (adminKey) headers['X-Admin-Key'] = adminKey
      const r = await fetch(url('/api/admin/restart_ollama'), { method: 'POST', headers })
      if (!r.ok) {
        const t = await r.text()
        setAdminError(r.status === 403 ? 'Invalid admin key' : `Admin error: ${r.status}`)
        throw new Error(t)
      }
      setAdminError('')
      pushToast('Ollama restart triggered', 'success')
    } catch (e) {
      pushToast('Failed to restart Ollama', 'error')
    } finally {
      setTimeout(() => checkOllama(), 1500)
      setPending('')
      setRestartingOllama(false)
    }
  }

  const changeModel = async (m: string) => {
    try {
      setSwitchingModel(true)
      setPending('Switching model...')
      const headers: any = { 'Content-Type': 'application/json' }
      if (adminKey) headers['X-Admin-Key'] = adminKey
      const r = await fetch(url('/api/ollama/set_model'), { method: 'POST', headers, body: JSON.stringify({ model: m }) })
      if (!r.ok) {
        const t = await r.text()
        setAdminError(r.status === 403 ? 'Invalid admin key' : `Admin error: ${r.status}`)
        throw new Error(t)
      }
      setAdminError('')
      setSelectedModel(m)
      await checkOllama()
      pushToast(`Model set to ${m}`, 'success')
    } catch (e) {
      pushToast('Failed to set model', 'error')
    } finally {
      setPending('')
      setSwitchingModel(false)
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

      <div className="card system" style={{ marginTop: 16 }}>
        <div className="system-header">
          <h2>System</h2>
        </div>
        <div className="system-grid">
          <div className="sys-card">
            <div className="sys-title">API</div>
            <div className="sys-body">
              <div className="stat">
                {checkingApi ? (<><span className="spinner"/> Checking…</>) : (<>
                  <span className={`dot ${apiOk ? 'ok' : 'down'}`}></span>
                  <span>{apiOk === null ? '—' : (apiOk ? 'Healthy' : 'Unreachable')}</span>
                </>)}
              </div>
              {!apiOk && apiError && <div className="error">{apiError}</div>}
              <div className="sys-actions">
                <button onClick={checkApi} disabled={checkingApi}>{checkingApi ? (<><span className="spinner" /> Checking…</>) : 'Check'}</button>
                <button onClick={restartApi} className="secondary" disabled={restartingApi}>{restartingApi ? (<><span className="spinner" /> Restarting…</>) : 'Restart'}</button>
              </div>
            </div>
          </div>
          <div className="sys-card">
            <div className="sys-title">Ollama</div>
            <div className="sys-body">
              <div className="stat">
                {checkingOllama ? (<><span className="spinner"/> Checking…</>) : (<>
                  <span className={`dot ${ollamaInfo ? 'ok' : 'down'}`}></span>
                  <span>{ollamaInfo ? (ollamaInfo.current_model || '—') : 'Unreachable'}</span>
                </>)}
              </div>
              {!ollamaInfo && ollamaError && <div className="error">{ollamaError}</div>}
              <div className="sys-actions">
                <button onClick={checkOllama} disabled={checkingOllama}>{checkingOllama ? (<><span className="spinner" /> Checking…</>) : 'Check'}</button>
                <button onClick={restartOllama} className="secondary" disabled={restartingOllama}>{restartingOllama ? (<><span className="spinner" /> Restarting…</>) : 'Restart'}</button>
              </div>
            </div>
          </div>
          <div className="sys-card">
            <div className="sys-title">Model</div>
            <div className="sys-body">
              <select value={selectedModel} onChange={(e) => changeModel(e.target.value)} disabled={switchingModel || !models.length}>
                <option value="">Select a model…</option>
                {models.map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
              <label style={{ marginTop: 10 }}>Admin key</label>
              <input type="password" value={adminKey} onChange={(e) => { setAdminKey(e.target.value); localStorage.setItem('adminKey', e.target.value) }} placeholder="Enter admin key" />
              {adminError && <div className="error" style={{ marginTop: 6 }}>{adminError}</div>}
              {!models.length && !checkingOllama && <div className="muted" style={{ marginTop: 6 }}>No models available</div>}
              {modelError && <div className="error" style={{ marginTop: 6 }}>{modelError}</div>}
            </div>
          </div>
        </div>
        {pending && <div className="muted" style={{ marginTop: 10 }}>{pending}</div>}
        {/* Toasts */}
        <div className="toast-wrap">
          {toasts.map(t => (
            <div key={t.id} className={`toast ${t.type}`}>{t.text}</div>
          ))}
        </div>
      </div>
    </div>
  )
}
