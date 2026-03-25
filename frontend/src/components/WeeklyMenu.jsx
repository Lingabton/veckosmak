import RecipeCard from './RecipeCard'
import SavingsBanner from './SavingsBanner'

export default function WeeklyMenu({ menu, onSwap, swapping, onShowShopping, onBack, onRegenerate, onFeedback, expandAll, setExpandAll, bonusOffers }) {
  if (!menu) return null

  return (
    <section className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <button onClick={onBack} className="text-sm transition-colors" style={{ color: 'var(--text-muted)' }}>
          Ändra inställningar
        </button>
        <button onClick={onShowShopping}
          className="text-sm font-medium px-4 py-1.5 rounded-full text-white transition-colors"
          style={{ backgroundColor: 'var(--accent)' }}>
          Inköpslista
        </button>
      </div>

      <div className="mb-5">
        <h1 className="text-2xl font-bold tracking-tight">Din veckomeny</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
          Vecka {menu.week_number}, {menu.year} — ICA Maxi Boglundsängen
        </p>
      </div>

      <SavingsBanner menu={menu} />

      <div className="flex items-center justify-between mb-4">
        <button onClick={() => setExpandAll(!expandAll)}
          className="text-xs transition-colors" style={{ color: 'var(--text-muted)' }}>
          {expandAll ? 'Dölj alla' : 'Visa alla recept'}
        </button>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        {menu.meals.map((meal, i) => (
          <RecipeCard key={meal.day} meal={meal} onSwap={onSwap} swapping={swapping}
            onFeedback={onFeedback} forceExpand={expandAll} index={i} />
        ))}
      </div>

      {/* Passa på — bonus offers not used in menu */}
      {bonusOffers && bonusOffers.length > 0 && (
        <div className="mt-10">
          <h2 className="text-lg font-bold tracking-tight mb-1">Passa på</h2>
          <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>
            Bra erbjudanden utanför din meny denna vecka
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            {bonusOffers.map((offer, i) => (
              <div key={offer.id || i} className="flex items-center justify-between p-3 rounded-xl border"
                style={{ backgroundColor: 'var(--surface)', borderColor: 'var(--border)' }}>
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">{offer.product_name}</p>
                  {offer.brand && <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{offer.brand}</p>}
                  {offer.quantity_deal && <p className="text-xs font-medium" style={{ color: 'var(--green)' }}>{offer.quantity_deal}</p>}
                </div>
                <div className="text-right shrink-0 ml-3">
                  <span className="font-bold" style={{ color: 'var(--accent)' }}>
                    {Math.round(offer.offer_price)} {offer.unit}
                  </span>
                  {offer.discount > 0 && (
                    <span className="block text-xs font-medium" style={{ color: 'var(--green)' }}>−{offer.discount}%</span>
                  )}
                  {offer.original_price && (
                    <span className="block text-xs line-through" style={{ color: 'var(--text-muted)' }}>
                      {Math.round(offer.original_price)}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-8 text-center">
        <button onClick={onRegenerate} className="text-sm transition-colors" style={{ color: 'var(--text-muted)' }}>
          Generera ny meny
        </button>
      </div>
    </section>
  )
}
