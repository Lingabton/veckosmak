import { useState } from 'react'

const DAY_NAMES = {
  monday: 'Måndag', tuesday: 'Tisdag', wednesday: 'Onsdag',
  thursday: 'Torsdag', friday: 'Fredag', saturday: 'Lördag', sunday: 'Söndag',
}

const SWAP_REASONS = [
  { label: 'Vill ha annat', value: '' },
  { label: 'Billigare', value: 'Vill ha ett billigare recept' },
  { label: 'Snabbare', value: 'Vill ha ett snabbare recept' },
  { label: 'Annan protein', value: 'Vill ha en annan proteinkälla' },
  { label: 'Nyttigare', value: 'Vill ha ett nyttigare recept' },
]

const DIFFICULTY_LABELS = { easy: 'Enkel', medium: 'Medel', hard: 'Avancerad' }

function kitchenRound(amount, unit) {
  if (amount <= 0) return 0
  if (['dl', 'msk', 'tsk'].includes(unit)) {
    if (amount <= 0.5) return 0.5
    return Math.round(amount * 2) / 2
  }
  if (unit === 'g') {
    if (amount < 50) return Math.round(amount / 5) * 5
    if (amount < 500) return Math.round(amount / 25) * 25
    return Math.round(amount / 50) * 50
  }
  if (unit === 'kg') return Math.round(amount * 10) / 10
  return Math.round(amount * 10) / 10
}

function CrowdRating({ score, count }) {
  if (!score || score <= 0) return null
  const full = Math.floor(score)
  const half = score - full >= 0.3
  return (
    <span className="inline-flex items-center gap-1 text-xs">
      <span className="flex">{[...Array(5)].map((_, i) => (
        <span key={i} className={i < full ? 'text-yellow-400' : (i === full && half) ? 'text-yellow-300' : 'text-gray-200'}>★</span>
      ))}</span>
      <span className="text-gray-400">{score.toFixed(1)}</span>
    </span>
  )
}

export default function RecipeCard({ meal, onSwap, swapping, onFeedback, forceExpand, index }) {
  const [expanded, setExpanded] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const { day, recipe, estimated_cost, estimated_cost_without_offers, offer_matches, scaled_servings, reasoning, popularity_score, is_fallback, mealprep_tip } = meal
  const savings = estimated_cost_without_offers - estimated_cost
  const pricePerPortion = scaled_servings > 0 ? Math.round(estimated_cost / scaled_servings) : 0
  const baseServings = recipe.servings || 4
  const scale = scaled_servings / baseServings
  const isExpanded = expanded || forceExpand

  const handleFeedback = (action) => {
    setFeedback(action)
    onFeedback?.(day, action)
  }

  return (
    <article className={`bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm animate-fade-in stagger-${(index || 0) + 1}`}>
      {/* Collapsed */}
      <div className="cursor-pointer" onClick={() => setExpanded(!expanded)}>
        {recipe.image_url ? (
          <div className="h-44 overflow-hidden bg-gray-100 recipe-img-overlay">
            <img src={recipe.image_url} alt={recipe.title} className="w-full h-full object-cover" loading="lazy" />
            {/* Day badge on image */}
            <div className="absolute top-3 left-3 z-10 bg-white/90 backdrop-blur-sm px-2.5 py-1 rounded-full text-xs font-semibold text-green-700 shadow-sm">
              {DAY_NAMES[day] || day}
            </div>
            {is_fallback && (
              <div className="absolute top-3 right-3 z-10 bg-amber-100/90 backdrop-blur-sm px-2 py-0.5 rounded-full text-xs text-amber-700">Auto</div>
            )}
          </div>
        ) : (
          <div className="h-20 bg-gradient-to-r from-green-50 to-green-100 flex items-center justify-center">
            <span className="text-xs font-semibold text-green-700 uppercase tracking-wide">{DAY_NAMES[day] || day}</span>
          </div>
        )}
        <div className="p-4">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="font-semibold text-gray-900">{recipe.title}</h3>
              <div className="flex items-center gap-2 mt-1">
                <CrowdRating score={popularity_score} count={recipe.rating_count || 0} />
                <span className="text-xs text-gray-400">{recipe.cook_time_minutes} min</span>
                <span className="text-xs text-gray-300">{DIFFICULTY_LABELS[recipe.difficulty]}</span>
              </div>
            </div>
          </div>

          {/* Compact offer count + quick swap */}
          <div className="flex items-center justify-between mt-2">
            {offer_matches && offer_matches.length > 0 ? (
              <p className="text-xs text-green-600 font-medium">
                {offer_matches.length} erbjudande{offer_matches.length > 1 ? 'n' : ''}
              </p>
            ) : <span />}
            <button
              onClick={(e) => { e.stopPropagation(); onSwap(day, '') }}
              disabled={swapping === day}
              className="text-xs text-gray-400 hover:text-orange-600 transition-colors px-2 py-1 -mr-2">
              {swapping === day ? '...' : '🔄 Byt'}
            </button>
          </div>

          <div className="flex items-center justify-between mt-1">
            <div className="text-sm">
              <span className="font-semibold" style={{ color: 'var(--accent)' }}>
                {Math.round(estimated_cost)} kr
              </span>
              <span className="text-gray-400 ml-1.5 text-xs">({pricePerPortion} kr/port)</span>
              {savings > 1 && <span className="text-green-600 ml-1.5 text-xs font-medium">-{Math.round(savings)} kr</span>}
            </div>
            <span className="text-xs text-green-700 font-medium">{isExpanded ? 'Dölj ▲' : 'Visa ▼'}</span>
          </div>
        </div>
      </div>

      {/* Expanded */}
      {isExpanded && (
        <div className="border-t border-gray-100 p-4 bg-gray-50 animate-expand">
          {reasoning && <p className="text-sm text-gray-500 italic mb-3">{reasoning}</p>}

          {/* Nutrition */}
          {recipe.nutrition && (
            <div className="flex gap-3 mb-3 text-xs">
              {recipe.nutrition.calories && (
                <span className="bg-orange-50 text-orange-700 px-2 py-1 rounded-lg font-medium">{recipe.nutrition.calories} kcal</span>
              )}
              {recipe.nutrition.protein && (
                <span className="bg-blue-50 text-blue-700 px-2 py-1 rounded-lg font-medium">{recipe.nutrition.protein}g protein</span>
              )}
              {recipe.nutrition.carbohydrates && (
                <span className="bg-yellow-50 text-yellow-700 px-2 py-1 rounded-lg">{recipe.nutrition.carbohydrates}g kolh</span>
              )}
              {recipe.nutrition.fat && (
                <span className="bg-purple-50 text-purple-700 px-2 py-1 rounded-lg">{recipe.nutrition.fat}g fett</span>
              )}
            </div>
          )}

          {mealprep_tip && (
            <div className="bg-blue-50 border border-blue-100 rounded-lg p-2.5 mb-3 text-xs text-blue-800">
              <span className="font-medium">💡 Mealprep:</span> {mealprep_tip}
            </div>
          )}

          {/* Offer details */}
          {offer_matches && offer_matches.length > 0 && (
            <div className="mb-3">
              <h4 className="text-xs font-medium text-gray-500 mb-1.5">Erbjudanden som används</h4>
              <div className="space-y-1">
                {offer_matches.map((o, i) => (
                  <div key={i} className="flex items-center justify-between text-xs bg-green-50 rounded-lg px-2.5 py-1.5">
                    <span className="text-gray-700">{o.product_name}</span>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-green-700">{Math.round(o.offer_price)} {o.unit}</span>
                      {o.original_price && <span className="text-gray-400 line-through">{Math.round(o.original_price)}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Ingredients */}
          <div className="mb-4">
            <h4 className="font-medium text-sm text-gray-900 mb-2">Ingredienser ({scaled_servings} port)</h4>
            <ul className="text-sm text-gray-700 space-y-1">
              {recipe.ingredients.map((ing, i) => {
                const scaledAmount = kitchenRound(ing.amount * scale, ing.unit)
                return (
                  <li key={i} className="flex items-start gap-1.5">
                    <span className="text-gray-300 mt-0.5">•</span>
                    <span>
                      {scaledAmount > 0 && <span className="text-gray-500">{scaledAmount} {ing.unit} </span>}
                      {ing.name}
                    </span>
                  </li>
                )
              })}
            </ul>
          </div>

          {/* Instructions */}
          <div className="mb-4">
            <h4 className="font-medium text-sm text-gray-900 mb-2">Gör så här</h4>
            <ol className="text-sm text-gray-700 space-y-2">
              {recipe.instructions.map((step, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-green-700 font-medium shrink-0">{i + 1}.</span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          </div>

          {recipe.source_url && (
            <a href={recipe.source_url} target="_blank" rel="noopener noreferrer"
              className="inline-block text-sm text-green-700 hover:text-green-800 underline mb-4">
              Originalrecept →
            </a>
          )}

          {/* Feedback */}
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs text-gray-400">Betyg:</span>
            {['liked', 'disliked'].map(action => (
              <button key={action} onClick={(e) => { e.stopPropagation(); handleFeedback(action) }}
                className={`w-11 h-11 rounded-full border text-lg transition-all ${
                  feedback === action
                    ? action === 'liked' ? 'bg-green-100 border-green-300 scale-110' : 'bg-red-100 border-red-300 scale-110'
                    : 'border-gray-200 hover:border-gray-400'
                }`}>
                {action === 'liked' ? '👍' : '👎'}
              </button>
            ))}
            {feedback && <span className="text-xs text-green-600 ml-1">Tack!</span>}
          </div>

          {/* Swap — direct button, no dropdown */}
          <button onClick={(e) => { e.stopPropagation(); onSwap(day, '') }}
            disabled={swapping === day}
            className="w-full py-2.5 text-sm border border-gray-300 rounded-lg hover:border-green-700 hover:text-green-700 disabled:opacity-50 transition-colors">
            {swapping === day ? (
              <span className="flex items-center justify-center gap-1.5">
                <span className="w-4 h-4 border-2 border-gray-300 border-t-green-700 rounded-full animate-spin" />
                Byter...
              </span>
            ) : '🔄 Byt recept'}
          </button>
        </div>
      )}
    </article>
  )
}
