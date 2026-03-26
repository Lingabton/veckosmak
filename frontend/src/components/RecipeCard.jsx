import { useState, useCallback } from 'react'

const DAY_NAMES = {
  monday: 'Måndag', tuesday: 'Tisdag', wednesday: 'Onsdag',
  thursday: 'Torsdag', friday: 'Fredag', saturday: 'Lördag', sunday: 'Söndag',
}

function kitchenRound(amount, unit, name = '') {
  if (amount <= 0) return 0
  // Skip silly items
  const nameLower = name.toLowerCase()
  if (nameLower.includes('vatten')) return 0 // Don't list water
  if (['dl', 'msk', 'tsk'].includes(unit)) return amount <= 0.5 ? 0.5 : Math.round(amount * 2) / 2
  if (unit === 'g') return amount < 50 ? Math.round(amount / 5) * 5 : amount < 500 ? Math.round(amount / 25) * 25 : Math.round(amount / 50) * 50
  return Math.round(amount * 10) / 10
}

function Stars({ score }) {
  if (!score || score <= 0) return null
  return (
    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
      <span className="text-amber-400">{'★'.repeat(Math.round(score))}</span> {score.toFixed(1)}
    </span>
  )
}

export default function RecipeCard({ meal, onSwap, swapping, onFeedback, forceExpand, index }) {
  const [expanded, setExpanded] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [alternatives, setAlternatives] = useState(null)
  const [loadingAlts, setLoadingAlts] = useState(false)
  const { day, recipe, estimated_cost, estimated_cost_without_offers, offer_matches, scaled_servings, reasoning, popularity_score, mealprep_tip } = meal

  const fetchAlternatives = useCallback(async () => {
    if (alternatives) { setAlternatives(null); return }
    setLoadingAlts(true)
    try {
      const menuId = meal._menuId || ''
      const resp = await fetch('/api/menu/alternatives', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ menu_id: menuId, day }),
      })
      if (resp.ok) {
        const data = await resp.json()
        setAlternatives(data.alternatives || [])
      }
    } catch {}
    setLoadingAlts(false)
  }, [day, alternatives, meal._menuId])
  const savings = estimated_cost_without_offers - estimated_cost
  const pricePerPortion = scaled_servings > 0 ? Math.round(estimated_cost / scaled_servings) : 0
  const scale = scaled_servings / (recipe.servings || 4)
  const isExpanded = expanded || forceExpand

  return (
    <article className={`rounded-2xl overflow-hidden border transition-shadow hover:shadow-md animate-fade-in stagger-${(index || 0) + 1}`}
      style={{ backgroundColor: 'var(--surface)', borderColor: 'var(--border)' }}>

      {/* Image + day badge */}
      <div className="cursor-pointer" onClick={() => setExpanded(!expanded)}>
        {recipe.image_url ? (
          <div className="h-48 overflow-hidden recipe-img-overlay">
            <img src={recipe.image_url} alt={recipe.title} className="w-full h-full object-cover" loading="lazy" />
            <div className="absolute top-3 left-3 z-10 bg-white/95 backdrop-blur-sm px-3 py-1 rounded-full text-xs font-semibold"
              style={{ color: 'var(--green-deep)' }}>
              {DAY_NAMES[day]}
            </div>
          </div>
        ) : (
          <div className="h-16 flex items-center px-5" style={{ backgroundColor: 'var(--green-soft)' }}>
            <span className="text-sm font-semibold" style={{ color: 'var(--green-deep)' }}>{DAY_NAMES[day]}</span>
          </div>
        )}

        <div className="p-4">
          <h3 className="font-semibold text-base leading-snug">{recipe.title}</h3>
          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
            <Stars score={popularity_score} />
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{recipe.cook_time_minutes} min</span>
            {offer_matches?.length > 0 && (
              <span className="text-xs font-medium" style={{ color: 'var(--green)' }}>
                {offer_matches.length} erbjudanden
              </span>
            )}
            {recipe.tags?.includes('barnvänlig') && (
              <span className="text-xs px-1.5 py-0.5 rounded" style={{ backgroundColor: '#fef3c7', color: '#92400e' }}>Barnvänlig</span>
            )}
          </div>

          <div className="flex items-center justify-between mt-3">
            <div className="flex items-baseline gap-2">
              <span className="text-lg font-bold" style={{ color: 'var(--accent)' }}>{Math.round(estimated_cost)} kr</span>
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{pricePerPortion} kr/port</span>
              {savings > 1 && <span className="text-xs font-medium" style={{ color: 'var(--green)' }}>−{Math.round(savings)} kr</span>}
            </div>
            <div className="flex items-center gap-2">
              <button onClick={(e) => { e.stopPropagation(); fetchAlternatives() }}
                disabled={swapping === day || loadingAlts}
                className="text-xs px-2.5 py-1 rounded-full border transition-colors hover:shadow-sm"
                style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>
                {loadingAlts ? '...' : 'Byt'}
              </button>
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                {isExpanded ? '▲' : '▼'}
              </span>
            </div>
          </div>

          {/* Quick swap alternatives — shown on collapsed card */}
          {alternatives && alternatives.length > 0 && (
            <div className="mt-3 pt-3 space-y-1.5 animate-expand" style={{ borderTop: '1px solid var(--border-light)' }}>
              <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>Byt till:</p>
              {alternatives.slice(0, 3).map(alt => (
                <button key={alt.recipe_id}
                  onClick={(e) => { e.stopPropagation(); setAlternatives(null); onSwap(day, '', alt.recipe_id) }}
                  disabled={swapping === day}
                  className="w-full text-left p-2.5 rounded-lg border transition-all hover:shadow-sm text-sm flex items-center justify-between"
                  style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg)' }}>
                  <div className="min-w-0">
                    <span className="font-medium">{alt.title}</span>
                    <div className="flex items-center gap-2 text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                      {alt.rating && <span className="text-amber-400">★ {alt.rating}</span>}
                      <span>{alt.cook_time_minutes} min</span>
                      {alt.is_favorite && <span style={{ color: 'var(--accent)' }}>Favorit</span>}
                    </div>
                  </div>
                  <span className="font-bold shrink-0 ml-2" style={{ color: 'var(--accent)' }}>{alt.price_per_portion} kr/p</span>
                </button>
              ))}
              <button onClick={(e) => { e.stopPropagation(); setAlternatives(null) }}
                className="w-full text-xs py-1" style={{ color: 'var(--text-muted)' }}>
                Avbryt
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Expanded */}
      {isExpanded && (
        <div className="px-4 pb-4 animate-expand" style={{ borderTop: '1px solid var(--border-light)' }}>
          <div className="pt-4">
            {reasoning && <p className="text-sm italic mb-3" style={{ color: 'var(--text-muted)' }}>{reasoning}</p>}

            {/* Nutrition */}
            {recipe.nutrition && (
              <div className="flex gap-3 mb-4 text-xs font-medium">
                {recipe.nutrition.calories && <span className="px-2.5 py-1 rounded-lg" style={{ backgroundColor: 'var(--accent-soft)', color: 'var(--accent)' }}>{recipe.nutrition.calories} kcal</span>}
                {recipe.nutrition.protein && <span className="px-2.5 py-1 rounded-lg" style={{ backgroundColor: '#eff6ff', color: '#2563eb' }}>{recipe.nutrition.protein}g protein</span>}
              </div>
            )}

            {mealprep_tip && (
              <p className="text-xs p-2.5 rounded-lg mb-4" style={{ backgroundColor: '#f0f9ff', color: '#0369a1' }}>
                <strong>Tips:</strong> {mealprep_tip}
              </p>
            )}

            {/* Offers */}
            {offer_matches?.length > 0 && (
              <div className="mb-4 space-y-1">
                {offer_matches.map((o, i) => (
                  <div key={i} className="flex justify-between text-xs py-1.5 px-3 rounded-lg" style={{ backgroundColor: 'var(--green-soft)' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>{o.product_name}</span>
                    <span>
                      <strong style={{ color: 'var(--green)' }}>{Math.round(o.offer_price)} {o.unit}</strong>
                      {o.original_price && <span className="ml-1.5 line-through" style={{ color: 'var(--text-muted)' }}>{Math.round(o.original_price)}</span>}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Ingredients */}
            <h4 className="font-medium text-sm mb-2">Ingredienser <span style={{ color: 'var(--text-muted)' }}>({scaled_servings} port)</span></h4>
            <ul className="text-sm space-y-0.5 mb-4" style={{ color: 'var(--text-secondary)' }}>
              {recipe.ingredients.map((ing, i) => {
                const amt = kitchenRound(ing.amount * scale, ing.unit, ing.name)
                if (amt === 0 && ing.amount > 0 && ing.name.toLowerCase().includes('vatten')) return null
                return <li key={i}>{amt > 0 && <span style={{ color: 'var(--text-muted)' }}>{amt} {ing.unit} </span>}{ing.name}</li>
              })}
            </ul>

            {/* Instructions */}
            <h4 className="font-medium text-sm mb-2">Instruktioner</h4>
            <ol className="text-sm space-y-2 mb-4" style={{ color: 'var(--text-secondary)' }}>
              {recipe.instructions.map((step, i) => (
                <li key={i} className="flex gap-2">
                  <span className="font-medium shrink-0" style={{ color: 'var(--green)' }}>{i + 1}.</span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>

            {recipe.source_url && (
              <a href={recipe.source_url} target="_blank" rel="noopener noreferrer"
                className="text-sm underline mb-4 inline-block" style={{ color: 'var(--green)' }}>
                Originalrecept
              </a>
            )}

            {/* Feedback + Alternatives */}
            <div className="mt-3 pt-3" style={{ borderTop: '1px solid var(--border-light)' }}>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Betyg:</span>
                {['liked', 'disliked'].map(action => (
                  <button key={action} onClick={(e) => { e.stopPropagation(); setFeedback(action); onFeedback?.(day, action) }}
                    className={`w-9 h-9 rounded-full border text-sm transition-all ${feedback === action ? 'scale-110 shadow-sm' : ''}`}
                    style={{
                      borderColor: feedback === action ? (action === 'liked' ? 'var(--green)' : '#ef4444') : 'var(--border)',
                      backgroundColor: feedback === action ? (action === 'liked' ? 'var(--green-soft)' : '#fef2f2') : 'transparent',
                    }}>
                    {action === 'liked' ? '↑' : '↓'}
                  </button>
                ))}
                {feedback && <span className="text-xs" style={{ color: 'var(--green)' }}>Tack!</span>}
              </div>

              {/* Show alternatives */}
              <button onClick={(e) => { e.stopPropagation(); fetchAlternatives() }}
                disabled={loadingAlts}
                className="w-full py-2 text-sm border rounded-lg transition-colors"
                style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
                {loadingAlts ? 'Hämtar alternativ...' : alternatives ? 'Dölj alternativ' : 'Visa alternativ'}
              </button>

              {alternatives && alternatives.length > 0 && (
                <div className="mt-3 space-y-2 animate-expand">
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Välj ett alternativ:</p>
                  {alternatives.map(alt => (
                    <button key={alt.recipe_id}
                      onClick={(e) => { e.stopPropagation(); onSwap(day, '', alt.recipe_id) }}
                      disabled={swapping === day}
                      className="w-full text-left p-3 rounded-xl border transition-all hover:shadow-sm"
                      style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg)' }}>
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium">{alt.title}</span>
                            {alt.is_favorite && (
                              <span className="text-xs px-1.5 py-0.5 rounded-full"
                                style={{ backgroundColor: '#fef3c7', color: '#92400e' }}>Favorit</span>
                            )}
                          </div>
                          <div className="flex items-center gap-2 mt-0.5 text-xs" style={{ color: 'var(--text-muted)' }}>
                            {alt.rating && <span className="text-amber-400">{'★'.repeat(Math.round(alt.rating))} {alt.rating}</span>}
                            <span>{alt.cook_time_minutes} min</span>
                            {alt.offer_matches > 0 && <span style={{ color: 'var(--green)' }}>{alt.offer_matches} erbjudanden</span>}
                          </div>
                        </div>
                        <span className="font-bold text-sm shrink-0" style={{ color: 'var(--accent)' }}>
                          {alt.price_per_portion} kr/port
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </article>
  )
}
