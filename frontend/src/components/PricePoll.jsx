import { useState } from 'react'

export default function PricePoll({ menuId }) {
  const pollKey = `veckosmak_poll_${menuId}`
  const [answered, setAnswered] = useState(() => !!localStorage.getItem(pollKey))
  const [thanks, setThanks] = useState(false)

  if (answered && !thanks) return null

  const submit = async (answer) => {
    localStorage.setItem(pollKey, answer)
    setAnswered(true)
    setThanks(true)
    setTimeout(() => setThanks(false), 3000)
    try {
      await fetch('/api/poll/price', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ menu_id: menuId, answer }),
      })
    } catch {}
  }

  if (thanks) {
    return (
      <div className="mt-4 py-2 px-3 rounded-lg text-center fade-in" style={{ background: 'var(--color-bg)', border: '1px solid var(--color-border-light)' }}>
        <p className="text-xs" style={{ color: 'var(--color-brand-dark)' }}>Tack för din feedback!</p>
      </div>
    )
  }

  return (
    <div className="mt-4 py-3 px-4 rounded-xl" style={{ background: 'var(--color-bg)', border: '1px solid var(--color-border-light)' }}>
      <p className="text-xs mb-2" style={{ color: 'var(--color-text-muted)' }}>
        Veckosmak är gratis. Vad skulle du betala?
      </p>
      <div className="flex gap-1.5 flex-wrap">
        {[
          { value: '0', label: 'Ingenting' },
          { value: '29', label: '29 kr/mån' },
          { value: '49', label: '49 kr/mån' },
          { value: '79', label: '79 kr/mån' },
        ].map(opt => (
          <button key={opt.value} onClick={() => submit(opt.value)}
            className="btn-pill text-xs px-3 py-1.5 hover:opacity-80 transition-opacity">
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  )
}
