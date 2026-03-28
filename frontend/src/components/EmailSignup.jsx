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
    <div className="card p-5 mt-8" style={{ background: 'var(--color-brand-light)', borderColor: 'var(--color-brand)' }}>
      <p className="font-bold text-sm mb-1" style={{ color: 'var(--color-brand-dark)' }}>
        Få veckans meny direkt i mejlen varje måndag
      </p>
      <p className="text-xs mb-3" style={{ color: 'var(--color-brand)' }}>
        Gratis — vi skickar en färdig veckomeny baserad på veckans bästa erbjudanden.
      </p>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          placeholder="din@mejl.se"
          required
          className="flex-1 px-3 py-2 text-sm border rounded-lg outline-none focus:ring-2 focus:ring-green-700"
          style={{ borderColor: 'var(--color-border)', background: 'white' }}
        />
        <button type="submit" disabled={loading} className="btn btn-primary text-sm px-4 py-2 shrink-0">
          {loading ? '...' : 'Prenumerera'}
        </button>
      </form>
      {error && <p className="text-xs mt-2" style={{ color: '#c92a2a' }}>{error}</p>}
    </div>
  )
}
