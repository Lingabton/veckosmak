import { useState } from 'react'

const SIGNED_UP_KEY = 'veckosmak_email_signup'

export default function EmailSignup({ context }) {
  const [email, setEmail] = useState('')
  const [done, setDone] = useState(() => !!localStorage.getItem(SIGNED_UP_KEY))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  if (done) return null

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!email.trim() || !email.includes('@')) return
    setLoading(true)
    setError(null)
    try {
      const resp = await fetch('/api/signup/email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() }),
      })
      if (!resp.ok) throw new Error('Något gick fel')
      localStorage.setItem(SIGNED_UP_KEY, email.trim())
      setDone(true)
    } catch {
      setError('Kunde inte spara. Försök igen.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mt-6 py-3 px-4 rounded-xl" style={{ background: 'var(--color-bg)', border: '1px solid var(--color-border-light)' }}>
      <form onSubmit={handleSubmit} className="flex items-center gap-2">
        <span className="text-xs shrink-0" style={{ color: 'var(--color-text-muted)' }}>Få menyn i mejlen:</span>
        <input
          type="email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          placeholder="din@mejl.se"
          required
          className="flex-1 min-w-0 px-2.5 py-1.5 text-xs border rounded-lg outline-none focus:ring-1 focus:ring-green-700"
          style={{ borderColor: 'var(--color-border)', background: 'white' }}
        />
        <button type="submit" disabled={loading} className="text-xs font-medium px-3 py-1.5 rounded-lg shrink-0 transition-colors"
          style={{ background: 'var(--color-brand)', color: 'white' }}>
          {loading ? '...' : 'Skicka'}
        </button>
      </form>
      {error && <p className="text-xs mt-1.5" style={{ color: '#c92a2a' }}>{error}</p>}
    </div>
  )
}
