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
      <div className="card p-4 mt-8 text-center fade-in" style={{ background: 'var(--color-brand-light)', borderColor: 'var(--color-brand)' }}>
        <p className="text-sm font-medium" style={{ color: 'var(--color-brand-dark)' }}>Tack för din feedback!</p>
      </div>
    )
  }

  return (
    <div className="card p-5 mt-8" style={{ borderColor: 'var(--color-border-light)' }}>
      <p className="font-bold text-sm mb-1">Veckosmak är gratis under lanseringen.</p>
      <p className="text-sm mb-3" style={{ color: 'var(--color-text-muted)' }}>
        Vad skulle du betala för den här tjänsten?
      </p>
      <div className="flex gap-2 flex-wrap">
        {[
          { value: '0', label: 'Ingenting' },
          { value: '29', label: '29 kr/mån' },
          { value: '49', label: '49 kr/mån' },
          { value: '79', label: '79 kr/mån' },
        ].map(opt => (
          <button key={opt.value} onClick={() => submit(opt.value)}
            className="btn-pill text-sm px-4 py-2 hover:opacity-80 transition-opacity">
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  )
}
