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

  const { day, recipe, estimated_cost, estimated_cost_without_offers, offer_matches, scaled_servings, reasoning, popularity_score, mealprep_tip } = meal
  const savings = estimated_cost_without_offers - estimated_cost
  const pp = scaled_servings > 0 ? Math.round(estimated_cost / scaled_servings) : 0
  const scale = scaled_servings / (recipe.servings || 4)
  const isExpanded = expanded || forceExpand

  const fetchAlts = useCallback(async () => {
    if (alts) { setAlts(null); return }
    setLoadingAlts(true)
    try {
      const r = await fetch('/api/menu/alternatives', {method:'POST',headers:{'Content-Type':'application/json'},
        body: JSON.stringify({menu_id:meal._menuId||'',day})})
      if (r.ok) { const d = await r.json(); setAlts(d.alternatives||[]) }
    } catch {}
    setLoadingAlts(false)
  }, [day, alts, meal._menuId])

  return (
    <article className={`card card-interactive overflow-hidden fade-up delay-${(index||0)+1}`}>
      {/* Image + overlay info */}
      <div className="cursor-pointer" onClick={() => setExpanded(!expanded)}>
        {recipe.image_url ? (
          <div className="h-52 overflow-hidden img-overlay relative">
            <img src={recipe.image_url} alt={recipe.title} className="w-full h-full object-cover" loading="lazy" />
            <div className="absolute top-3 left-3 z-10">
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-white/90 backdrop-blur-sm shadow-sm"
                style={{color:'var(--color-brand-dark)'}}>{DAY_NAMES[day]}</span>
            </div>
          </div>
        ) : (
          <div className="h-20 flex items-center px-5" style={{background:'var(--color-brand-light)'}}>
            <span className="font-bold" style={{color:'var(--color-brand-dark)'}}>{DAY_NAMES[day]}</span>
          </div>
        )}

        <div className="p-4">
          <h3 className="font-bold text-base leading-snug">{recipe.title}</h3>

          <div className="flex items-center gap-2 mt-1.5 text-xs flex-wrap" style={{color:'var(--color-text-muted)'}}>
            {popularity_score > 0 && <span className="text-amber-400">{'★'.repeat(Math.round(popularity_score))} <span className="text-gray-400">{popularity_score.toFixed(1)}</span></span>}
            <span>{recipe.cook_time_minutes} min</span>
            {offer_matches?.length > 0 && <span style={{color:'var(--color-brand)'}}>{offer_matches.length} erbjudanden</span>}
            {recipe.tags?.includes('barnvänlig') && <span style={{background:'#fef3c7',color:'#92400e',padding:'1px 6px',borderRadius:'4px'}}>Barnvänlig</span>}
          </div>

          <div className="flex items-center justify-between mt-3">
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold" style={{color:'var(--color-accent)'}}>{Math.round(estimated_cost)} kr</span>
              <span className="text-xs" style={{color:'var(--color-text-muted)'}}>{pp} kr/port</span>
              {savings > 1 && <span className="text-xs font-semibold" style={{color:'var(--color-brand)'}}>−{Math.round(savings)} kr</span>}
            </div>
            <div className="flex items-center gap-2">
              <button onClick={e=>{e.stopPropagation();fetchAlts()}} disabled={swapping===day||loadingAlts}
                className="btn-secondary text-xs px-3 py-1.5 rounded-full">
                {loadingAlts?'...':'Byt'}
              </button>
              <span className="text-xs" style={{color:'var(--color-text-muted)'}}>{isExpanded?'▲':'▼'}</span>
            </div>
          </div>

          {/* Quick swap alternatives */}
          {alts && alts.length > 0 && (
            <div className="mt-3 pt-3 space-y-1.5 expand" style={{borderTop:'1px solid var(--color-border-light)'}}>
              <p className="text-xs" style={{color:'var(--color-text-muted)'}}>Byt till:</p>
              {alts.slice(0,3).map(alt => (
                <button key={alt.recipe_id} onClick={e=>{e.stopPropagation();setAlts(null);onSwap(day,'',alt.recipe_id)}}
                  className="card w-full text-left p-3 flex items-center justify-between text-sm" disabled={swapping===day}>
                  <div>
                    <span className="font-medium">{alt.title}</span>
                    <div className="flex items-center gap-2 text-xs mt-0.5" style={{color:'var(--color-text-muted)'}}>
                      {alt.rating && <span className="text-amber-400">★ {alt.rating}</span>}
                      <span>{alt.cook_time_minutes} min</span>
                      {alt.is_favorite && <span className="font-semibold" style={{color:'var(--color-accent)'}}>Favorit</span>}
                    </div>
                  </div>
                  <span className="font-bold shrink-0 ml-2" style={{color:'var(--color-accent)'}}>{alt.price_per_portion} kr/p</span>
                </button>
              ))}
              <button onClick={e=>{e.stopPropagation();setAlts(null)}} className="w-full text-xs py-1" style={{color:'var(--color-text-muted)'}}>Avbryt</button>
            </div>
          )}
        </div>
      </div>

      {/* Expanded details */}
      {isExpanded && (
        <div className="px-4 pb-4 expand" style={{borderTop:'1px solid var(--color-border-light)'}}>
          <div className="pt-4">
            {reasoning && <p className="text-sm italic mb-3" style={{color:'var(--color-text-muted)'}}>{reasoning}</p>}

            {recipe.nutrition && (
              <div className="flex gap-2 mb-3">
                {recipe.nutrition.calories && <span className="text-xs font-medium px-2.5 py-1 rounded-lg" style={{background:'var(--color-accent-light)',color:'var(--color-accent)'}}>{recipe.nutrition.calories} kcal</span>}
                {recipe.nutrition.protein && <span className="text-xs font-medium px-2.5 py-1 rounded-lg" style={{background:'#eff6ff',color:'#2563eb'}}>{recipe.nutrition.protein}g protein</span>}
              </div>
            )}

            {mealprep_tip && <p className="text-xs p-3 rounded-xl mb-3" style={{background:'#f0f9ff',color:'#0369a1'}}><b>Tips:</b> {mealprep_tip}</p>}

            {offer_matches?.length > 0 && (
              <div className="mb-4 space-y-1">
                {offer_matches.map((o,i) => (
                  <div key={i} className="flex justify-between text-xs py-1.5 px-3 rounded-lg" style={{background:'var(--color-brand-light)'}}>
                    <span>{o.product_name}</span>
                    <span><b style={{color:'var(--color-brand)'}}>{Math.round(o.offer_price)} {o.unit}</b>
                    {o.original_price && <span className="ml-1.5 line-through" style={{color:'var(--color-text-muted)'}}>{Math.round(o.original_price)}</span>}</span>
                  </div>
                ))}
              </div>
            )}

            <h4 className="font-bold text-sm mb-2">Ingredienser <span style={{color:'var(--color-text-muted)',fontWeight:400}}>({scaled_servings} port)</span></h4>
            <ul className="text-sm space-y-0.5 mb-4" style={{color:'var(--color-text-secondary)'}}>
              {recipe.ingredients.map((ing,i) => {
                const amt = kitchenRound(ing.amount*scale, ing.unit, ing.name)
                if (amt===0 && ing.amount>0 && ing.name.toLowerCase().includes('vatten')) return null
                return <li key={i}>{amt>0&&<span style={{color:'var(--color-text-muted)'}}>{amt} {ing.unit} </span>}{ing.name}</li>
              })}
            </ul>

            <h4 className="font-bold text-sm mb-2">Gör så här</h4>
            <ol className="text-sm space-y-2 mb-4" style={{color:'var(--color-text-secondary)'}}>
              {recipe.instructions.map((step,i) => (
                <li key={i} className="flex gap-2">
                  <span className="font-bold shrink-0" style={{color:'var(--color-brand)'}}>{i+1}.</span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>

            {recipe.source_url && <a href={recipe.source_url} target="_blank" rel="noopener noreferrer"
              className="text-sm font-medium mb-3 inline-block" style={{color:'var(--color-brand)'}}>Originalrecept →</a>}

            <div className="flex items-center gap-2 pt-3 mt-2" style={{borderTop:'1px solid var(--color-border-light)'}}>
              <span className="text-xs" style={{color:'var(--color-text-muted)'}}>Betyg:</span>
              {['liked','disliked'].map(a => (
                <button key={a} onClick={e=>{e.stopPropagation();setFeedback(a);onFeedback?.(day,a)}}
                  className={`stepper-btn text-sm ${feedback===a?'scale-110':''}`}
                  style={{borderColor:feedback===a?(a==='liked'?'var(--color-brand)':'#e03131'):'var(--color-border)',
                    background:feedback===a?(a==='liked'?'var(--color-brand-light)':'#fff5f5'):'transparent'}}>
                  {a==='liked'?'👍':'👎'}
                </button>
              ))}
              {feedback && <span className="text-xs font-medium" style={{color:'var(--color-brand)'}}>Tack!</span>}
            </div>
          </div>
        </div>
      )}
    </article>
  )
}
