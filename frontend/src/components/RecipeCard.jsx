import { useState, useCallback } from 'react'

const DAY_NAMES = {monday:'Måndag',tuesday:'Tisdag',wednesday:'Onsdag',thursday:'Torsdag',friday:'Fredag',saturday:'Lördag',sunday:'Söndag'}

function kitchenRound(amt, unit, name='') {
  if (amt <= 0 || name.toLowerCase().includes('vatten')) return 0
  if (['dl','msk','tsk'].includes(unit)) return amt<=0.5?0.5:Math.round(amt*2)/2
  if (unit==='g') return amt<50?Math.round(amt/5)*5:amt<500?Math.round(amt/25)*25:Math.round(amt/50)*50
  return Math.round(amt*10)/10
}

export default function RecipeCard({ meal, onSwap, swapping, onFeedback, forceExpand, index }) {
  const [expanded, setExpanded] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [alts, setAlts] = useState(null)
  const [loadingAlts, setLoadingAlts] = useState(false)

  const { day, recipe, estimated_cost, estimated_cost_without_offers, offer_matches, scaled_servings, reasoning, popularity_score, mealprep_tip, side_suggestion } = meal
  const savings = estimated_cost_without_offers - estimated_cost
  const pp = scaled_servings > 0 ? Math.round(estimated_cost / scaled_servings) : 0
  const scale = scaled_servings / (recipe.servings || 4)
  const isExpanded = expanded || forceExpand
  // Only show well-known chefs (not "Torbjörn - Arvika")
  const KNOWN_CHEFS = new Set([
    'Per Morberg','Johan Jureskog','Leila Lindholm','Tommy Myllymäki',
    'Tina Nordström','Jamie Oliver','Markus Aujalay','Niklas Ekstedt',
    'Lisa Lemke','Ernst Kirchsteiger','Mathias Dahlgren','Leif Mannerström',
    'Paul Svensson','Marcus Samuelsson','Filip Fastén','Gert Klötzke',
    'Christian Hellberg','Alexandra Zazzi','Pernilla Wahlgren','Lotta Lundgren',
    'Nigella Lawson','Pontus Frithiof','Danyel Couet','Magnus Ek',
    'Camilla Läckberg','Kocklandslaget',
  ])
  const chefTag = recipe.tags?.find(t => t.startsWith('kock:'))
  const rawChefName = chefTag ? chefTag.slice(5) : null
  const chefName = rawChefName && KNOWN_CHEFS.has(rawChefName) ? rawChefName : null

  const fetchAlts = useCallback(async () => {
    if (alts) { setAlts(null); return }
    setLoadingAlts(true)
    try {
      const r = await fetch('/api/menu/alternatives', {method:'POST',headers:{'Content-Type':'application/json'},
        body: JSON.stringify({menu_id: meal._menuId||'', day, exclude_recipe_ids: meal._allRecipeIds||[]})})
      if (r.ok) { const d = await r.json(); setAlts(d.alternatives||[]) }
    } catch {}
    setLoadingAlts(false)
  }, [day, alts, meal._menuId, meal._allRecipeIds])

  return (
    <article className={`card overflow-hidden fade-up delay-${(index||0)+1}`} style={{
      transition: 'box-shadow 0.3s ease, transform 0.3s ease',
    }}>
      {/* Image + overlay */}
      <div className="cursor-pointer" onClick={() => setExpanded(!expanded)}>
        {recipe.image_url ? (
          <div className="h-64 overflow-hidden relative group">
            <img
              src={recipe.image_url}
              alt={recipe.title}
              className="w-full h-full object-cover transition-transform duration-700 ease-out group-hover:scale-105"
              loading="lazy"
            />
            {/* Cinematic gradient overlay */}
            <div className="absolute inset-0" style={{
              background: 'linear-gradient(180deg, rgba(0,0,0,0.08) 0%, rgba(0,0,0,0) 30%, rgba(0,0,0,0.5) 75%, rgba(0,0,0,0.7) 100%)',
            }} />

            {/* Glass morphism day badge — top left */}
            <div className="absolute top-4 left-4 z-10">
              <span className="px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wide" style={{
                background: 'rgba(255,255,255,0.2)',
                backdropFilter: 'blur(12px)',
                WebkitBackdropFilter: 'blur(12px)',
                color: 'white',
                border: '1px solid rgba(255,255,255,0.25)',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
              }}>
                {DAY_NAMES[day]}
              </span>
            </div>

            {/* Offer match dots — top right */}
            {offer_matches?.length > 0 && (
              <div className="absolute top-4 right-4 z-10 flex items-center gap-1">
                {offer_matches.slice(0, 4).map((_, i) => (
                  <div key={i} className="w-2 h-2 rounded-full" style={{
                    background: '#4ade80',
                    boxShadow: '0 0 6px rgba(74,222,128,0.5)',
                  }} />
                ))}
                {offer_matches.length > 4 && (
                  <span className="text-[10px] font-medium ml-0.5" style={{ color: 'rgba(255,255,255,0.8)' }}>
                    +{offer_matches.length - 4}
                  </span>
                )}
              </div>
            )}

            {/* Quick time badge if fast — bottom of image */}
            {recipe.cook_time_minutes <= 20 && (
              <div className="absolute bottom-3 right-4 z-10">
                <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full" style={{
                  background: 'rgba(255,255,255,0.2)',
                  backdropFilter: 'blur(8px)',
                  WebkitBackdropFilter: 'blur(8px)',
                  color: 'white',
                  border: '1px solid rgba(255,255,255,0.2)',
                }}>
                  {recipe.cook_time_minutes} min
                </span>
              </div>
            )}
          </div>
        ) : (
          <div className="h-24 flex items-center px-6 relative" style={{
            background: 'linear-gradient(135deg, var(--color-brand-light) 0%, rgba(232,245,233,0.4) 100%)',
          }}>
            <span className="font-bold text-lg" style={{ color: 'var(--color-brand-dark)' }}>{DAY_NAMES[day]}</span>
          </div>
        )}

        {/* Content area */}
        <div className="px-5 pt-4 pb-4">
          {/* Title + chef */}
          <div className="mb-2">
            <h3 className="font-bold text-[17px] leading-tight tracking-tight" style={{ color: 'var(--color-text)' }}>
              {recipe.title}
            </h3>
            {chefName && (
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded" style={{
                  background: 'var(--color-bg)',
                  color: 'var(--color-text-secondary)',
                  letterSpacing: '0.02em',
                }}>
                  {chefName}
                </span>
                <span className="text-[11px]" style={{ color: 'var(--color-text-muted)' }}>
                  {recipe.source}
                </span>
              </div>
            )}
          </div>

          {/* Meta line */}
          <div className="flex items-center gap-2 text-xs flex-wrap" style={{ color: 'var(--color-text-muted)' }}>
            {popularity_score > 0 && (
              <span className="flex items-center gap-0.5">
                <span className="text-amber-400">{'★'.repeat(Math.round(popularity_score))}</span>
                <span>{popularity_score.toFixed(1)}</span>
              </span>
            )}
            {recipe.cook_time_minutes > 20 && <span>{recipe.cook_time_minutes} min</span>}
            {recipe.tags?.includes('barnvänlig') && (
              <span className="font-medium px-1.5 py-0.5 rounded" style={{
                background: '#fef3c7', color: '#92400e', fontSize: '10px',
              }}>Barnvänlig</span>
            )}
          </div>

          {/* Price row */}
          <div className="flex items-end justify-between mt-3.5">
            <div className="flex items-baseline gap-3">
              <div>
                <span className="font-display text-2xl font-bold" style={{ color: 'var(--color-text)' }}>
                  {Math.round(estimated_cost)}
                </span>
                <span className="text-sm font-display ml-0.5" style={{ color: 'var(--color-text-muted)' }}>kr</span>
              </div>
              <span className="text-[11px]" style={{ color: 'var(--color-text-muted)' }}>{pp} kr/port</span>
              {savings > 1 && (
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-full" style={{
                  background: 'rgba(22,163,74,0.08)',
                  color: '#16a34a',
                }}>
                  Sparar {Math.round(savings)} kr
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              {/* Ghost "Byt" button */}
              <button
                onClick={e => { e.stopPropagation(); fetchAlts() }}
                disabled={swapping === day || loadingAlts}
                className="text-xs font-medium px-3.5 py-1.5 rounded-full transition-all duration-200"
                style={{
                  color: 'var(--color-text-muted)',
                  border: '1.5px solid var(--color-border)',
                  background: 'transparent',
                  cursor: swapping === day || loadingAlts ? 'not-allowed' : 'pointer',
                  opacity: swapping === day || loadingAlts ? 0.5 : 1,
                }}
                onMouseEnter={e => {
                  if (swapping !== day && !loadingAlts) {
                    e.currentTarget.style.borderColor = 'var(--color-brand)'
                    e.currentTarget.style.color = 'var(--color-brand)'
                    e.currentTarget.style.background = 'var(--color-brand-light)'
                    e.currentTarget.style.transform = 'translateY(-1px)'
                  }
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = 'var(--color-border)'
                  e.currentTarget.style.color = 'var(--color-text-muted)'
                  e.currentTarget.style.background = 'transparent'
                  e.currentTarget.style.transform = 'translateY(0)'
                }}
              >
                {loadingAlts ? '...' : 'Byt'}
              </button>
              <span className="text-[11px] select-none" style={{ color: 'var(--color-text-muted)', opacity: 0.5 }}>
                {isExpanded ? '▲' : '▼'}
              </span>
            </div>
          </div>

          {/* Swap alternatives — card-in-card */}
          {alts && alts.length > 0 && (
            <div className="mt-4 pt-4 space-y-2 expand" style={{ borderTop: '1px solid var(--color-border-light)' }}>
              <p className="text-[11px] uppercase tracking-widest font-medium" style={{ color: 'var(--color-text-muted)' }}>
                Byt till
              </p>
              {alts.slice(0, 3).map(alt => {
                const altChef = alt.tags?.find(t => t.startsWith('kock:'))
                const altRawChef = altChef ? altChef.slice(5) : null
                const altChefName = altRawChef && KNOWN_CHEFS.has(altRawChef) ? altRawChef : null
                return (
                  <button
                    key={alt.recipe_id}
                    onClick={e => { e.stopPropagation(); setAlts(null); onSwap(day, '', alt.recipe_id) }}
                    disabled={swapping === day}
                    className="w-full text-left p-3.5 rounded-xl flex items-center justify-between transition-all duration-200"
                    style={{
                      background: 'var(--color-bg)',
                      border: '1px solid var(--color-border-light)',
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.background = 'var(--color-brand-light)'
                      e.currentTarget.style.borderColor = 'rgba(26,92,53,0.15)'
                      e.currentTarget.style.transform = 'translateX(4px)'
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.background = 'var(--color-bg)'
                      e.currentTarget.style.borderColor = 'var(--color-border-light)'
                      e.currentTarget.style.transform = 'translateX(0)'
                    }}
                  >
                    <div className="min-w-0">
                      <span className="font-semibold text-sm">{alt.title}</span>
                      <div className="flex items-center gap-2 text-[11px] mt-1 flex-wrap" style={{ color: 'var(--color-text-muted)' }}>
                        {altChefName && (
                          <span className="font-medium" style={{ color: 'var(--color-text-secondary)' }}>{altChefName}</span>
                        )}
                        {alt.rating && <span className="text-amber-400">★ {alt.rating}</span>}
                        <span>{alt.cook_time_minutes} min</span>
                        {alt.offer_matches > 0 && (
                          <span style={{color:'var(--color-brand)'}}>{alt.offer_matches} erbjudanden</span>
                        )}
                      </div>
                    </div>
                    <div className="text-right shrink-0 ml-3">
                      <span className="font-display font-bold text-sm" style={{ color: 'var(--color-accent)' }}>
                        {alt.price_per_portion} kr/port
                      </span>
                      {alt.estimated_cost && pp > 0 && alt.price_per_portion < pp && (
                        <p className="text-[10px] font-medium" style={{color:'#16a34a'}}>
                          {pp - alt.price_per_portion} kr billigare
                        </p>
                      )}
                      {alt.estimated_cost && pp > 0 && alt.price_per_portion > pp && (
                        <p className="text-[10px]" style={{color:'var(--color-text-muted)'}}>
                          +{alt.price_per_portion - pp} kr dyrare
                        </p>
                      )}
                    </div>
                  </button>
                )
              })}
              <button
                onClick={e => { e.stopPropagation(); setAlts(null) }}
                className="w-full text-[11px] py-1.5 font-medium transition-colors"
                style={{ color: 'var(--color-text-muted)' }}
              >
                Avbryt
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Expanded details */}
      {isExpanded && (
        <div className="px-5 pb-5 expand" style={{ borderTop: '1px solid var(--color-border-light)' }}>
          <div className="pt-5">
            {/* Reasoning */}
            {reasoning && (
              <div className="text-xs leading-relaxed p-3.5 rounded-xl mb-4" style={{
                background: 'var(--color-bg)',
                color: 'var(--color-text-secondary)',
                borderLeft: '3px solid var(--color-brand)',
              }}>
                <span className="font-semibold" style={{ color: 'var(--color-brand)' }}>Varför detta recept</span>
                <span className="mx-1.5" style={{ color: 'var(--color-border)' }}>|</span>
                {reasoning}
              </div>
            )}
            {(!reasoning || reasoning.includes('Automatiskt vald')) && (
              <div className="text-xs leading-relaxed p-3.5 rounded-xl mb-4" style={{
                background: 'var(--color-bg)', color: 'var(--color-text-secondary)',
                borderLeft: '3px solid var(--color-brand)',
              }}>
                <span className="font-semibold" style={{color:'var(--color-brand)'}}>Varför detta recept</span>
                <span className="mx-1.5" style={{color:'var(--color-border)'}}>|</span>
                {offer_matches?.length > 0
                  ? `${offer_matches.length} ingrediens${offer_matches.length > 1 ? 'er' : ''} på kampanj från din butik. Pris per portion: ${pp} kr.`
                  : `Populärt recept med betyg ${popularity_score > 0 ? popularity_score.toFixed(1) + '/5' : 'från ica.se'}. Pris per portion: cirka ${pp} kr.`
                }
              </div>
            )}

            {/* Nutrition pills */}
            {recipe.nutrition && (
              <div className="flex gap-2 mb-4">
                {recipe.nutrition.calories && (
                  <span className="inline-flex items-center gap-1 text-xs font-medium px-3 py-1.5 rounded-full" style={{
                    background: 'var(--color-accent-light)',
                    color: 'var(--color-accent)',
                  }}>
                    <span style={{ fontSize: '13px' }}>🔥</span>
                    {recipe.nutrition.calories} kcal
                  </span>
                )}
                {recipe.nutrition.protein && (
                  <span className="inline-flex items-center gap-1 text-xs font-medium px-3 py-1.5 rounded-full" style={{
                    background: '#eff6ff',
                    color: '#2563eb',
                  }}>
                    <span style={{ fontSize: '13px' }}>💪</span>
                    {recipe.nutrition.protein}g protein
                  </span>
                )}
              </div>
            )}

            {/* Mealprep tip */}
            {mealprep_tip && (
              <p className="text-xs leading-relaxed p-3.5 rounded-xl mb-4" style={{
                background: '#f0f9ff',
                color: '#0369a1',
              }}>
                <span className="font-semibold">Tips:</span> {mealprep_tip}
              </p>
            )}

            {/* Offer matches — subtle indicators */}
            {offer_matches?.length > 0 && (
              <div className="mb-5">
                <p className="text-[11px] uppercase tracking-widest font-medium mb-2" style={{ color: 'var(--color-text-muted)' }}>
                  Erbjudanden som används
                </p>
                <div className="grid gap-1.5">
                  {offer_matches.map((o, i) => (
                    <div key={i} className="flex items-center justify-between text-xs py-2 px-3 rounded-lg" style={{
                      background: 'rgba(232,245,233,0.5)',
                      border: '1px solid rgba(26,92,53,0.06)',
                    }}>
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: '#16a34a' }} />
                        <span style={{ color: 'var(--color-text-secondary)' }}>{o.product_name}</span>
                      </div>
                      <span>
                        <b style={{ color: 'var(--color-brand)' }}>{Math.round(o.offer_price)} {o.unit}</b>
                        {o.original_price && (
                          <span className="ml-1.5 line-through" style={{ color: 'var(--color-text-muted)' }}>
                            {Math.round(o.original_price)}
                          </span>
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Ingredients — 2-column grid on desktop */}
            <h4 className="font-bold text-sm mb-3 flex items-baseline gap-2">
              Ingredienser
              <span className="font-normal text-xs" style={{ color: 'var(--color-text-muted)' }}>
                {scaled_servings} portioner
              </span>
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 mb-5">
              {recipe.ingredients.map((ing, i) => {
                const amt = kitchenRound(ing.amount * scale, ing.unit, ing.name)
                if (amt === 0 && ing.amount > 0 && ing.name.toLowerCase().includes('vatten')) return null
                return (
                  <div key={i} className="flex items-baseline py-1 text-sm" style={{
                    borderBottom: '1px solid var(--color-border-light)',
                  }}>
                    {amt > 0 && (
                      <span className="shrink-0 w-16 text-xs tabular-nums" style={{ color: 'var(--color-text-muted)' }}>
                        {amt} {ing.unit}
                      </span>
                    )}
                    <span style={{ color: 'var(--color-text-secondary)' }}>{ing.name}</span>
                  </div>
                )
              })}
            </div>

            {/* Instructions */}
            <h4 className="font-bold text-sm mb-3">Gör så här</h4>
            <ol className="space-y-3 mb-5">
              {recipe.instructions.map((step, i) => (
                <li key={i} className="flex gap-3 text-sm leading-relaxed">
                  <span className="shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold" style={{
                    background: 'var(--color-brand-light)',
                    color: 'var(--color-brand)',
                  }}>
                    {i + 1}
                  </span>
                  <span style={{ color: 'var(--color-text-secondary)' }} dangerouslySetInnerHTML={{
                    __html: step
                      .replace(/(\d+\s*(?:min|minuter|sekunder|timmar?))/gi, '<b>$1</b>')
                      .replace(/(Stek|Koka|Vispa|Hacka|Skala|Skär|Blanda|Rör|Tillsätt|Häll|Stek|Grilla|Ugn|Sjud|Smält)/g, '<b>$1</b>')
                  }} />
                </li>
              ))}
            </ol>

            {/* Cost breakdown — polished table */}
            {meal.cost_details?.length > 0 && (
              <details className="mb-4 group">
                <summary className="text-[11px] uppercase tracking-widest font-medium cursor-pointer flex items-center gap-2 py-2" style={{
                  color: 'var(--color-text-muted)',
                }}>
                  <span>Så räknar vi</span>
                  <span style={{ color: 'var(--color-border)' }}>—</span>
                  <span className="font-display font-bold text-xs normal-case tracking-normal" style={{ color: 'var(--color-text-secondary)' }}>
                    {Math.round(estimated_cost)} kr totalt
                  </span>
                </summary>
                <div className="mt-2 rounded-xl overflow-hidden" style={{
                  border: '1px solid var(--color-border-light)',
                }}>
                  {meal.cost_details.map((cd, i) => (
                    <div key={i} className="flex justify-between text-xs py-2.5 px-4" style={{
                      background: cd.source === 'erbjudande' ? 'rgba(232,245,233,0.4)' : (i % 2 === 0 ? 'var(--color-surface)' : 'var(--color-bg)'),
                      borderBottom: i < meal.cost_details.length - 1 ? '1px solid var(--color-border-light)' : 'none',
                    }}>
                      <span style={{ color: 'var(--color-text-secondary)' }}>
                        {cd.amount > 0 && (
                          <span className="tabular-nums" style={{ color: 'var(--color-text-muted)' }}>
                            {cd.amount} {cd.unit}{' '}
                          </span>
                        )}
                        {cd.ingredient}
                      </span>
                      <span className="shrink-0 ml-3 flex items-center gap-1">
                        <span className="font-medium tabular-nums">{Math.round(cd.cost)} kr</span>
                        {cd.source === 'erbjudande' && (
                          <span className="w-1.5 h-1.5 rounded-full" style={{ background: '#16a34a' }} />
                        )}
                        {cd.source === 'uppskattad' && (
                          <span style={{ color: 'var(--color-text-muted)', fontSize: '10px' }}>~</span>
                        )}
                      </span>
                    </div>
                  ))}
                  <div className="px-4 py-2 text-[10px] flex items-center gap-3" style={{
                    background: 'var(--color-bg)',
                    color: 'var(--color-text-muted)',
                    borderTop: '1px solid var(--color-border-light)',
                  }}>
                    <span className="flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ background: '#16a34a' }} />
                      på kampanj
                    </span>
                    <span>~ uppskattad kostnad</span>
                  </div>
                </div>
              </details>
            )}

            {/* Source link */}
            {recipe.source_url && (
              <a
                href={recipe.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-medium inline-flex items-center gap-1 mb-4 transition-colors"
                style={{ color: 'var(--color-brand)' }}
                onMouseEnter={e => { e.currentTarget.style.color = 'var(--color-brand-dark)' }}
                onMouseLeave={e => { e.currentTarget.style.color = 'var(--color-brand)' }}
              >
                Originalrecept
                <span style={{ fontSize: '12px' }}>→</span>
              </a>
            )}

            {/* Feedback */}
            <div className="flex items-center gap-3 pt-4 mt-2" style={{ borderTop: '1px solid var(--color-border-light)' }}>
              <span className="text-[11px] uppercase tracking-widest font-medium" style={{ color: 'var(--color-text-muted)' }}>
                Betyg
              </span>
              <div className="flex items-center gap-1.5">
                {['liked', 'disliked'].map(a => (
                  <button
                    key={a}
                    onClick={e => { e.stopPropagation(); setFeedback(a); onFeedback?.(day, a) }}
                    className="w-9 h-9 rounded-full flex items-center justify-center text-sm transition-all duration-200"
                    style={{
                      border: `1.5px solid ${feedback === a ? (a === 'liked' ? 'var(--color-brand)' : '#e03131') : 'var(--color-border)'}`,
                      background: feedback === a ? (a === 'liked' ? 'var(--color-brand-light)' : '#fff5f5') : 'transparent',
                      transform: feedback === a ? 'scale(1.1)' : 'scale(1)',
                    }}
                  >
                    {a === 'liked' ? '👍' : '👎'}
                  </button>
                ))}
              </div>
              {feedback && (
                <span className="text-xs font-semibold" style={{
                  background: 'linear-gradient(135deg, #16a34a, #059669)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text',
                }}>
                  Tack!
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </article>
  )
}
