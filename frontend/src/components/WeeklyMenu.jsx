import { useState } from 'react'
import RecipeCard from './RecipeCard'
import SavingsBanner from './SavingsBanner'

export default function WeeklyMenu({ menu, onSwap, swapping, onShowShopping, onBack, onRegenerate, onFeedback, expandAll, setExpandAll, bonusOffers }) {
  const [confirmRegenerate, setConfirmRegenerate] = useState(false)
  if (!menu) return null

  const handleRegenerate = () => {
    if (!confirmRegenerate) { setConfirmRegenerate(true); return }
    setConfirmRegenerate(false)
    onRegenerate()
  }

  return (
    <section className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <button onClick={onBack} className="text-sm" style={{ color: 'var(--text-muted)' }}>
          Ändra inställningar
        </button>
        <button onClick={onShowShopping}
          className="text-sm font-medium px-4 py-1.5 rounded-full text-white"
          style={{ backgroundColor: 'var(--accent)' }}>
          Inköpslista
        </button>
      </div>

      <div className="mb-5">
        <h1 className="text-2xl font-bold tracking-tight">Din veckomeny</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
          {menu.date_range || `Vecka ${menu.week_number}`} — {menu.store_name || 'ICA'}
        </p>
        {/* Active filters (#11) */}
        {menu.active_filters && menu.active_filters.length > 0 && (
          <div className="flex gap-1.5 mt-2">
            {menu.active_filters.map(f => (
              <span key={f} className="text-xs px-2 py-0.5 rounded-full" style={{ backgroundColor: 'var(--green-soft)', color: 'var(--green)' }}>
                {f}
              </span>
            ))}
          </div>
        )}
      </div>

      <SavingsBanner menu={menu} />

      <div className="flex items-center justify-between mb-4">
        <button onClick={() => setExpandAll(!expandAll)}
          className="text-xs" style={{ color: 'var(--text-muted)' }}>
          {expandAll ? 'Dölj alla' : 'Visa alla recept'}
        </button>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        {menu.meals.map((meal, i) => (
          <RecipeCard key={meal.day} meal={{...meal, _menuId: menu.id}} onSwap={onSwap} swapping={swapping}
            onFeedback={onFeedback} forceExpand={expandAll} index={i} />
        ))}
      </div>

      {/* Passa på — grouped by category */}
      {bonusOffers && bonusOffers.length > 0 && (
        <div className="mt-10">
          <h2 className="text-lg font-bold tracking-tight mb-1">Passa på</h2>
          <p className="text-sm mb-5" style={{ color: 'var(--text-muted)' }}>
            Bra priser utanför din meny denna vecka
          </p>
          <div className="space-y-5">
            {bonusOffers.map((group, gi) => (
              <div key={gi}>
                <h3 className="text-sm font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>
                  {group.label}
                </h3>
                <div className="grid gap-2 sm:grid-cols-2">
                  {group.offers.map((offer, i) => (
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
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Next step — clear CTA */}
      <div className="card p-5 mt-8 text-center">
        <p className="font-bold text-base mb-1">Nöjd med menyn?</p>
        <p className="text-sm mb-4" style={{ color: 'var(--color-text-muted)' }}>
          Inköpslistan är redo — öppna den i butiken och bocka av.
        </p>
        <button onClick={onShowShopping} className="btn btn-primary w-full mb-3">
          Visa inköpslista
        </button>
        <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
          Din meny och inköpslista sparas automatiskt — du kan stänga appen och öppna den igen i butiken.
        </p>
      </div>

      {/* Regenerate */}
      <div className="mt-6 text-center">
        {confirmRegenerate ? (
          <div className="fade-in">
            <p className="text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>Nuvarande meny försvinner. Fortsätta?</p>
            <div className="flex justify-center gap-3">
              <button onClick={handleRegenerate}
                className="btn btn-primary text-sm px-5 py-2">
                Ja, generera ny
              </button>
              <button onClick={() => setConfirmRegenerate(false)}
                className="btn btn-secondary text-sm px-5 py-2">
                Avbryt
              </button>
            </div>
          </div>
        ) : (
          <button onClick={handleRegenerate} className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
            Generera ny meny
          </button>
        )}
      </div>
    </section>
  )
}
