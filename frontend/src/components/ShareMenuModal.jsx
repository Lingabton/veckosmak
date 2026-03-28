import { useState } from 'react'

export default function ShareMenuModal({ onClose, menu, userEmail }) {
  const currentWeek = Math.ceil(
    ((new Date() - new Date(new Date().getFullYear(), 0, 1)) / 86400000 + new Date(new Date().getFullYear(), 0, 1).getDay() + 1) / 7
  )

  const [title, setTitle] = useState(menu?.title || `Veckomeny v${menu?.week_number || currentWeek}`)
  const [description, setDescription] = useState('')
  const [sharing, setSharing] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  const handleShare = async (e) => {
    e.preventDefault()
    if (!title.trim() || !menu?.id || !userEmail) return
    setSharing(true)
    setError(null)
    try {
      const resp = await fetch('/api/community/share', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          menu_id: menu.id,
          title: title.trim(),
          description: description.trim(),
          email: userEmail,
        }),
        signal: AbortSignal.timeout(10000),
      })
      if (!resp.ok) throw new Error('Kunde inte dela menyn')
      const data = await resp.json()
      setSuccess(data.share_url || data.url || true)
    } catch (e) {
      setError(e.message)
    } finally {
      setSharing(false)
    }
  }

  const totalCost = menu?.total_cost || 0
  const totalSavings = menu?.total_savings || 0
  const numMeals = menu?.meals?.length || 0

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.4)' }}>
      <div className="card p-6 w-full max-w-md fade-up" style={{ background: 'var(--color-surface)' }}>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold">Dela din meny</h2>
          <button onClick={onClose} className="text-sm" style={{ color: 'var(--color-text-muted)' }}>✕</button>
        </div>

        {success ? (
          <div className="text-center py-4 fade-in">
            <p className="text-3xl mb-3">🎉</p>
            <p className="font-bold text-base mb-1">Menyn är delad!</p>
            <p className="text-sm mb-4" style={{ color: 'var(--color-text-muted)' }}>
              Andra kan nu se och inspireras av din veckomeny.
            </p>
            {typeof success === 'string' && (
              <div className="mb-4">
                <label className="text-xs font-medium block mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                  Delningslänk
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={success}
                    readOnly
                    className="flex-1 px-3 py-2 text-xs border rounded-lg"
                    style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg)' }}
                  />
                  <button
                    onClick={() => {
                      navigator.clipboard?.writeText(success)
                    }}
                    className="btn-pill text-xs shrink-0"
                  >
                    Kopiera
                  </button>
                </div>
              </div>
            )}
            <button onClick={onClose} className="btn btn-secondary text-sm">Stäng</button>
          </div>
        ) : (
          <form onSubmit={handleShare}>
            {/* Preview */}
            <div className="p-3 rounded-lg mb-4" style={{ background: 'var(--color-bg)' }}>
              <p className="text-xs font-medium mb-2" style={{ color: 'var(--color-text-secondary)' }}>
                Förhandsgranskning
              </p>
              <div className="flex items-center gap-3 text-sm">
                <span className="font-bold">{numMeals} middagar</span>
                <span style={{ color: 'var(--color-accent)' }}>
                  {Math.round(totalCost)} kr
                </span>
                {totalSavings > 0 && (
                  <span className="font-medium" style={{ color: 'var(--color-brand)' }}>
                    −{Math.round(totalSavings)} kr
                  </span>
                )}
              </div>
              {menu?.meals && menu.meals.length > 0 && (
                <div className="mt-2 space-y-0.5">
                  {menu.meals.slice(0, 5).map((meal, i) => (
                    <p key={i} className="text-xs truncate" style={{ color: 'var(--color-text-muted)' }}>
                      {meal.recipe?.title || meal.title}
                    </p>
                  ))}
                  {menu.meals.length > 5 && (
                    <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                      +{menu.meals.length - 5} till...
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Title */}
            <div className="mb-3">
              <label className="text-xs font-medium block mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Titel
              </label>
              <input
                type="text"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="Ge din meny en titel"
                required
                className="w-full px-4 py-2.5 text-sm border rounded-lg outline-none focus:ring-2 focus:ring-green-700"
                style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg)' }}
              />
            </div>

            {/* Description */}
            <div className="mb-4">
              <label className="text-xs font-medium block mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Beskrivning (valfritt)
              </label>
              <textarea
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="Berätta om din meny, t.ex. vilka erbjudanden du hittade..."
                rows={3}
                className="w-full px-4 py-2.5 text-sm border rounded-lg outline-none focus:ring-2 focus:ring-green-700 resize-none"
                style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg)' }}
              />
            </div>

            {/* Error */}
            {error && (
              <p className="text-xs mb-3 fade-in" style={{ color: '#c92a2a' }}>{error}</p>
            )}

            {/* Actions */}
            <div className="flex gap-2">
              <button type="submit" disabled={sharing || !title.trim()}
                className="btn btn-primary flex-1 text-sm py-2.5">
                {sharing ? 'Delar...' : 'Dela'}
              </button>
              <button type="button" onClick={onClose}
                className="btn btn-secondary text-sm px-5 py-2.5">
                Avbryt
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
