import { useState } from 'react'

const CATEGORY_LABELS = {
  all: 'Alla',
  meat: 'Kött',
  fish: 'Fisk',
  dairy: 'Mejeri',
  produce: 'Grönt',
  pantry: 'Skafferi',
  frozen: 'Fryst',
  bakery: 'Bröd',
  other: 'Övrigt',
}

export default function TopOffers({ offers, preferences, setPreferences, onGenerate, onBack, loading, loadingOffers }) {
  const [filter, setFilter] = useState('all')
  const pinned = new Set(preferences.pinned_offer_ids || [])
  const togglePin = (id) => {
    const next = new Set(pinned)
    if (next.has(id)) next.delete(id); else next.add(id)
    setPreferences({ ...preferences, pinned_offer_ids: [...next] })
  }

  if (loadingOffers) {
    return (
      <div className="text-center py-16 fade-in">
        <div className="w-8 h-8 border-2 rounded-full animate-spin mx-auto mb-4"
          style={{ borderColor: 'var(--color-border)', borderTopColor: 'var(--color-brand)' }} />
        <p className="font-semibold mb-1">Hämtar veckans erbjudanden</p>
        <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Från din butik — kan ta upp till 30 sek</p>
      </div>
    )
  }

  // Get unique categories from offers
  const categories = ['all', ...new Set(offers.map(o => o.category || 'other'))]
  const filtered = filter === 'all' ? offers : offers.filter(o => (o.category || 'other') === filter)

  return (
    <div className="fade-up">
      <div className="flex items-center justify-between mb-6">
        <button onClick={onBack} className="text-sm" style={{ color: 'var(--color-text-muted)' }}>← Tillbaka</button>
        <button onClick={onGenerate} disabled={loading}
          className="text-sm font-medium" style={{ color: 'var(--color-accent)' }}>
          Hoppa över →
        </button>
      </div>

      <h1 className="text-2xl font-bold tracking-tight mb-1">Veckans erbjudanden</h1>
      <p className="text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>
        Välj de erbjudanden du vill bygga menyn kring. Vi matchar recept som använder dem.
      </p>
      <p className="text-xs mb-4" style={{ color: 'var(--color-text-muted)' }}>
        {offers.length} erbjudanden · Sorterade efter bäst rabatt · Tryck för att välja
      </p>

      {/* Category filter tabs */}
      {offers.length > 0 && (
        <div className="flex gap-1.5 overflow-x-auto pb-2 mb-4 no-scrollbar">
          {categories.map(cat => (
            <button key={cat} onClick={() => setFilter(cat)}
              className={`btn-pill text-xs whitespace-nowrap ${filter === cat ? 'active' : ''}`}>
              {CATEGORY_LABELS[cat] || cat}
            </button>
          ))}
        </div>
      )}

      {offers.length === 0 ? (
        <div className="card p-4 text-sm mb-6" style={{ background: '#fffbeb', color: '#92400e' }}>
          Inga erbjudanden hittades. Du kan fortfarande generera en meny baserad på våra recept.
        </div>
      ) : filtered.length === 0 ? (
        <div className="card p-4 text-sm mb-6" style={{ background: 'var(--color-bg)', color: 'var(--color-text-muted)' }}>
          Inga erbjudanden i denna kategori.
        </div>
      ) : (
        <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 mb-6">
          {filtered.map((offer, i) => {
            const isPinned = pinned.has(offer.id)
            const discount = offer.discount || (offer.original_price ? Math.round((1 - offer.offer_price / offer.original_price) * 100) : 0)
            return (
              <button key={offer.id} onClick={() => togglePin(offer.id)}
                className={`card card-interactive text-left p-4 border-2 transition-all ${isPinned ? 'scale-[1.02]' : ''}`}
                style={{
                  borderColor: isPinned ? 'var(--color-brand)' : 'transparent',
                  background: isPinned ? 'var(--color-brand-light)' : 'var(--color-surface)',
                }}>
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-semibold text-sm">{offer.product_name}</p>
                    {offer.brand && <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{offer.brand}</p>}
                    {offer.quantity_deal && <p className="text-xs font-medium mt-0.5" style={{ color: 'var(--color-brand)' }}>{offer.quantity_deal}</p>}
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-lg font-bold" style={{ color: 'var(--color-accent)' }}>
                      {Math.round(offer.offer_price)} <span className="text-xs font-normal">{offer.unit}</span>
                    </p>
                    {discount > 0 && <p className="text-xs font-bold" style={{ color: 'var(--color-brand)' }}>−{discount}%</p>}
                    {offer.original_price && (
                      <p className="text-xs line-through" style={{ color: 'var(--color-text-muted)' }}>{Math.round(offer.original_price)}</p>
                    )}
                  </div>
                </div>
                {isPinned && (
                  <div className="mt-2 text-xs font-semibold" style={{ color: 'var(--color-brand-dark)' }}>
                    ✓ Vald — vi bygger menyn kring denna
                  </div>
                )}
                {i === 0 && !isPinned && filter === 'all' && (
                  <div className="mt-2 text-xs font-medium px-2 py-0.5 rounded-full inline-block"
                    style={{ background: 'var(--color-accent-light)', color: 'var(--color-accent)' }}>
                    Bästa rabatten
                  </div>
                )}
              </button>
            )
          })}
        </div>
      )}

      <div className="space-y-3">
        <button onClick={onGenerate} disabled={loading} className="btn btn-primary w-full">
          {loading ? 'Skapar meny...' : pinned.size > 0 ? `Skapa meny med ${pinned.size} valda erbjudanden` : 'Skapa meny med alla erbjudanden'}
        </button>
        {pinned.size === 0 && (
          <p className="text-center text-xs" style={{ color: 'var(--color-text-muted)' }}>
            Inga valda = vi väljer de smartaste kombinationerna
          </p>
        )}
      </div>
    </div>
  )
}
