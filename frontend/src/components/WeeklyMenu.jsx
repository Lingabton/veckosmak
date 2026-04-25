import { useState } from 'react'
import RecipeCard from './RecipeCard'
import SavingsBanner from './SavingsBanner'

const DIETS = [
  {v:'vegetarian',l:'Vegetarisk'},{v:'vegan',l:'Vegansk'},{v:'glutenfree',l:'Glutenfri'},
  {v:'dairyfree',l:'Mjölkfri'},{v:'lactosefree',l:'Laktosfri'},{v:'porkfree',l:'Fläskfri'},
]

export default function WeeklyMenu({ menu, onSwap, swapping, onShowShopping, onBack, onRegenerate, onFeedback, expandAll, setExpandAll, bonusOffers, preferences, setPreferences }) {
  const [confirmRegenerate, setConfirmRegenerate] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [settingsChanged, setSettingsChanged] = useState(false)
  if (!menu) return null

  const handleRegenerate = () => {
    if (!confirmRegenerate && !settingsChanged) { setConfirmRegenerate(true); return }
    setConfirmRegenerate(false)
    setSettingsChanged(false)
    setShowSettings(false)
    onRegenerate()
  }

  const update = (k, v) => {
    if (setPreferences) {
      setPreferences({...preferences, [k]: v})
      setSettingsChanged(true)
    }
  }
  const toggleDiet = (v) => {
    const c = preferences?.dietary_restrictions || []
    update('dietary_restrictions', c.includes(v) ? c.filter(d => d !== v) : [...c, v])
  }

  return (
    <section className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <button onClick={onBack} className="text-sm font-medium px-3 py-1.5 rounded-full"
          style={{ color: 'var(--color-brand-dark)', border: '1px solid var(--color-brand-dark)' }}>
          ← Ny meny
        </button>
        <button onClick={onShowShopping}
          className="text-sm font-medium px-4 py-1.5 rounded-full text-white"
          style={{ backgroundColor: 'var(--color-accent)' }}>
          Inköpslista
        </button>
      </div>

      <div className="mb-5">
        <h1 className="font-display text-3xl font-bold" style={{ letterSpacing: '-0.03em' }}>Din veckomeny</h1>
        <p className="text-sm mt-1 flex items-center gap-2 flex-wrap" style={{ color: 'var(--text-muted)' }}>
          <span className="text-xs font-medium px-2 py-0.5 rounded" style={{background:'var(--color-brand-light)',color:'var(--color-brand-dark)'}}>
            {menu.store_name || 'ICA'}
          </span>
          <span>{menu.date_range || `Vecka ${menu.week_number}`}</span>
          {menu.store_id && (
            <a href={`/api/stores/leaflet?store_id=${menu.store_id}`} target="_blank" rel="noopener noreferrer"
              className="font-medium" style={{ color: 'var(--color-brand)' }}>
              Se erbjudanden
            </a>
          )}
        </p>

        {/* Interactive settings strip */}
        {preferences && (
          <div className="mt-3">
            <div className="flex flex-wrap items-center gap-2">
              {/* Tappable badges */}
              <button onClick={() => setShowSettings(!showSettings)}
                className="text-xs px-2.5 py-1 rounded-full transition-all"
                style={{
                  background: showSettings ? 'var(--color-brand-light)' : 'var(--color-border-light)',
                  color: showSettings ? 'var(--color-brand-dark)' : 'var(--color-text-secondary)',
                  border: showSettings ? '1px solid var(--color-brand)' : '1px solid transparent',
                }}>
                {preferences.household_size} pers · {menu.meals?.length} middagar
                {preferences.budget_per_week ? ` · ${preferences.budget_per_week} kr` : ''}
                <span className="ml-1 opacity-50">{showSettings ? '▲' : '✎'}</span>
              </button>

              {menu.active_filters?.map(f => (
                <span key={f} className="text-xs px-2 py-0.5 rounded-full" style={{ backgroundColor: 'var(--green-soft)', color: 'var(--green)' }}>
                  {f}
                </span>
              ))}

              {settingsChanged && (
                <button onClick={handleRegenerate}
                  className="text-xs font-semibold px-3 py-1 rounded-full text-white fade-in"
                  style={{ background: 'var(--color-accent)' }}>
                  Uppdatera meny
                </button>
              )}
            </div>

            {/* Expandable inline settings */}
            {showSettings && (
              <div className="card p-4 mt-3 expand">
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="text-xs font-medium mb-1.5 block" style={{color:'var(--color-text-muted)'}}>Antal personer</label>
                    <div className="flex items-center gap-2">
                      <button className="stepper-btn" style={{width:36,height:36,fontSize:16}}
                        onClick={() => update('household_size', Math.max(1, preferences.household_size - 1))}>−</button>
                      <span className="text-lg font-bold w-6 text-center">{preferences.household_size}</span>
                      <button className="stepper-btn" style={{width:36,height:36,fontSize:16}}
                        onClick={() => update('household_size', Math.min(8, preferences.household_size + 1))}>+</button>
                    </div>
                  </div>
                  <div>
                    <label className="text-xs font-medium mb-1.5 block" style={{color:'var(--color-text-muted)'}}>Middagar</label>
                    <div className="flex items-center gap-2">
                      <button className="stepper-btn" style={{width:36,height:36,fontSize:16}}
                        onClick={() => update('num_dinners', Math.max(1, preferences.num_dinners - 1))}>−</button>
                      <span className="text-lg font-bold w-6 text-center">{preferences.num_dinners}</span>
                      <button className="stepper-btn" style={{width:36,height:36,fontSize:16}}
                        onClick={() => update('num_dinners', Math.min(7, preferences.num_dinners + 1))}>+</button>
                    </div>
                  </div>
                </div>

                <div className="mb-4">
                  <label className="text-xs font-medium mb-1.5 block" style={{color:'var(--color-text-muted)'}}>Kostfilter</label>
                  <div className="flex flex-wrap gap-1.5">
                    {DIETS.map(d => (
                      <button key={d.v} onClick={() => toggleDiet(d.v)}
                        className={`btn-pill text-xs ${(preferences.dietary_restrictions||[]).includes(d.v) ? 'active' : ''}`}>
                        {d.l}
                      </button>
                    ))}
                  </div>
                </div>

                {settingsChanged && (
                  <button onClick={handleRegenerate}
                    className="btn btn-primary w-full py-3 text-sm">
                    Skapa ny meny med dessa inställningar
                  </button>
                )}
                {!settingsChanged && (
                  <p className="text-xs text-center" style={{color:'var(--color-text-muted)'}}>
                    Ändra inställningar ovan för att generera en ny meny
                  </p>
                )}
              </div>
            )}
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
          <RecipeCard key={meal.day} meal={{...meal, _menuId: menu.id, _allRecipeIds: menu.meals.map(m=>m.recipe.id)}} onSwap={onSwap} swapping={swapping}
            onFeedback={onFeedback} forceExpand={expandAll} index={i} />
        ))}
      </div>

      {/* Passa på — grouped by category */}
      {bonusOffers && bonusOffers.length > 0 && (
        <div className="mt-10">
          <h2 className="text-lg font-bold tracking-tight mb-1">Passa på</h2>
          <p className="text-sm mb-5" style={{ color: 'var(--color-text-muted)' }}>
            Bra priser på basvaror — tryck + för att lägga till på inköpslistan
          </p>
          <div className="space-y-5">
            {bonusOffers.map((group, gi) => (
              <div key={gi}>
                <h3 className="text-sm font-semibold mb-2" style={{ color: 'var(--color-text-secondary)' }}>
                  {group.label}
                </h3>
                <div className="grid gap-2 sm:grid-cols-2">
                  {group.offers.map((offer, i) => (
                    <div key={offer.id || i} className="card flex items-center justify-between p-3">
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{offer.product_name}</p>
                        {offer.brand && <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{offer.brand}</p>}
                        {offer.quantity_deal && <p className="text-xs font-medium" style={{ color: 'var(--color-brand)' }}>{offer.quantity_deal}</p>}
                      </div>
                      <div className="flex items-center gap-2 shrink-0 ml-3">
                        <div className="text-right">
                          <span className="font-bold" style={{ color: 'var(--color-accent)' }}>
                            {Math.round(offer.offer_price)} {offer.unit}
                          </span>
                          {offer.discount > 0 && (
                            <span className="block text-xs font-medium" style={{ color: 'var(--color-brand)' }}>{offer.discount} % rabatt</span>
                          )}
                        </div>
                        <button onClick={(e) => {
                          const custom = JSON.parse(localStorage.getItem('veckosmak_custom_items') || '[]')
                          const name = `${offer.product_name}${offer.brand ? ' ('+offer.brand+')' : ''}`
                          if (!custom.includes(name)) {
                            custom.push(name)
                            localStorage.setItem('veckosmak_custom_items', JSON.stringify(custom))
                            const btn = e.currentTarget
                            btn.textContent = '✓'
                            btn.style.background = 'var(--color-brand-light)'
                            btn.style.color = 'var(--color-brand)'
                            btn.style.borderColor = 'var(--color-brand)'
                            setTimeout(() => { btn.textContent = '+'; btn.style.background = ''; btn.style.color = ''; btn.style.borderColor = '' }, 1500)
                          }
                        }}
                          className="stepper-btn text-sm" style={{width:32,height:32,fontSize:16}}
                          aria-label={`Lägg till ${offer.product_name} på inköpslistan`}
                          title="Lägg till på inköpslistan">+</button>
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
        {menu.id && (
          <a href={`/api/export/menu/${menu.id}`} target="_blank" rel="noopener noreferrer"
            className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
            Ladda ner PDF
          </a>
        )}
        <p className="text-xs mt-3" style={{ color: 'var(--color-text-muted)' }}>
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
