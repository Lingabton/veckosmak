export default function TopOffers({ offers, preferences, setPreferences, onGenerate, onBack, loading, loadingOffers }) {
  const pinned = new Set(preferences.pinned_offer_ids || [])
  const togglePin = (id) => {
    const next = new Set(pinned)
    if (next.has(id)) next.delete(id); else next.add(id)
    setPreferences({ ...preferences, pinned_offer_ids: [...next] })
  }

  if (loadingOffers) {
    return (
      <div className="text-center py-16 animate-fade-in">
        <div className="w-6 h-6 border-2 rounded-full animate-spin mx-auto mb-3"
          style={{ borderColor: 'var(--border)', borderTopColor: 'var(--green)' }} />
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Hämtar veckans erbjudanden...</p>
      </div>
    )
  }

  const sorted = [...offers].sort((a, b) => {
    const da = a.original_price ? (1 - a.offer_price / a.original_price) : 0
    const db = b.original_price ? (1 - b.offer_price / b.original_price) : 0
    return db - da
  })

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <button onClick={onBack} className="text-sm" style={{ color: 'var(--text-muted)' }}>Tillbaka</button>
        <button onClick={onGenerate} disabled={loading}
          className="text-sm font-medium" style={{ color: 'var(--accent)' }}>
          Hoppa över
        </button>
      </div>

      <h1 className="text-2xl font-bold tracking-tight mb-1">Veckans bästa erbjudanden</h1>
      <p className="text-sm mb-6" style={{ color: 'var(--text-secondary)' }}>
        Välj de du vill bygga menyn kring, eller hoppa över.
      </p>

      {offers.length === 0 ? (
        <div className="rounded-xl p-4 text-sm mb-6" style={{ backgroundColor: '#fffbeb', color: '#92400e' }}>
          Inga erbjudanden just nu. Du kan fortfarande generera en meny.
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 mb-6">
          {sorted.map((offer, i) => {
            const isPinned = pinned.has(offer.id)
            const discount = offer.original_price ? Math.round((1 - offer.offer_price / offer.original_price) * 100) : null
            return (
              <button key={offer.id} onClick={() => togglePin(offer.id)}
                className="text-left p-4 rounded-xl border-2 transition-all"
                style={{
                  borderColor: isPinned ? 'var(--green)' : 'var(--border)',
                  backgroundColor: isPinned ? 'var(--green-soft)' : 'var(--surface)',
                }}>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-medium text-sm">{offer.product_name}</p>
                    {offer.brand && <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{offer.brand}</p>}
                  </div>
                  <div className="text-right shrink-0">
                    <p className="font-bold" style={{ color: 'var(--accent)' }}>{Math.round(offer.offer_price)} {offer.unit}</p>
                    {discount > 0 && <p className="text-xs font-medium" style={{ color: 'var(--green)' }}>−{discount}%</p>}
                  </div>
                </div>
                {offer.original_price && (
                  <p className="text-xs mt-1 line-through" style={{ color: 'var(--text-muted)' }}>
                    Ord. {Math.round(offer.original_price)} {offer.unit}
                  </p>
                )}
                {i === 0 && (
                  <span className="inline-block mt-2 text-xs font-medium px-2 py-0.5 rounded-full"
                    style={{ backgroundColor: 'var(--accent-soft)', color: 'var(--accent)' }}>
                    Bästa rabatten
                  </span>
                )}
              </button>
            )
          })}
        </div>
      )}

      <button onClick={onGenerate} disabled={loading}
        className="w-full py-3.5 rounded-xl text-white font-semibold text-base disabled:opacity-50 transition-colors"
        style={{ backgroundColor: 'var(--accent)' }}>
        {loading ? 'Skapar meny...' : pinned.size > 0 ? `Skapa meny med ${pinned.size} erbjudanden` : 'Skapa meny'}
      </button>
    </div>
  )
}
