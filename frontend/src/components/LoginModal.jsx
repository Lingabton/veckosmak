import { useState, useEffect } from 'react'

export default function LoginModal({ onClose, onLogin }) {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  // Check for auth token in URL hash on mount
  useEffect(() => {
    const hash = window.location.hash
    const match = hash.match(/auth=([a-f0-9]+)/)
    if (match) {
      verifyToken(match[1])
      window.history.replaceState(null, '', window.location.pathname)
    }
  }, [])

  const verifyToken = async (token) => {
    try {
      const resp = await fetch(`/api/auth/verify?token=${token}`)
      if (resp.ok) {
        const data = await resp.json()
        onLogin?.(data.email)
      }
    } catch {}
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!email.trim()) return
    setLoading(true)
    setError(null)
    try {
      const resp = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() }),
        signal: AbortSignal.timeout(10000),
      })
      if (!resp.ok) throw new Error('Kunde inte skicka inloggningslänk')
      setSent(true)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.4)' }}>
      <div className="card p-6 w-full max-w-sm fade-up" style={{ background: 'var(--color-surface)' }}>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold">Logga in</h2>
          <button onClick={onClose} className="text-sm" style={{ color: 'var(--color-text-muted)' }}>✕</button>
        </div>

        {sent ? (
          <div className="text-center py-4">
            <p className="text-2xl mb-2">📧</p>
            <p className="font-semibold mb-1">Kolla din e-post!</p>
            <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
              Vi har skickat en inloggningslänk till <b>{email}</b>
            </p>
            <button onClick={onClose} className="btn btn-secondary mt-4 text-sm">Stäng</button>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <p className="text-sm mb-4" style={{ color: 'var(--color-text-secondary)' }}>
              Ange din e-post — vi skickar en inloggningslänk.
            </p>
            <input
              type="email" value={email} onChange={e => setEmail(e.target.value)}
              placeholder="din@epost.se" autoFocus required
              className="w-full px-4 py-3 text-sm border rounded-lg outline-none focus:ring-2 focus:ring-green-700 mb-3"
              style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg)' }}
            />
            {error && <p className="text-xs mb-3" style={{ color: '#c92a2a' }}>{error}</p>}
            <button type="submit" disabled={loading} className="btn btn-primary w-full">
              {loading ? 'Skickar...' : 'Skicka inloggningslänk'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
