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
    return Math.round(amount * 2) / 2  // Round to nearest 0.5
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
      <span className="flex">
        {[...Array(5)].map((_, i) => (
          <span key={i} className={i < full ? 'text-yellow-400' : (i === full && half) ? 'text-yellow-300' : 'text-gray-200'}>★</span>
        ))}
      </span>
      <span className="text-gray-400">{score.toFixed(1)}{count > 0 && ` (${count})`}</span>
    </span>
  )
}

function NutritionBadges({ nutrition }) {
  if (!nutrition) return null
  return (
    <div className="flex gap-2 text-xs text-gray-500 mt-1">
      {nutrition.calories && <span>{nutrition.calories} kcal</span>}
      {nutrition.protein && <span>{nutrition.protein}g protein</span>}
      {nutrition.carbohydrates && <span>{nutrition.carbohydrates}g kolhydrater</span>}
      {nutrition.fat && <span>{nutrition.fat}g fett</span>}
    </div>
  )
}

export default function RecipeCard({ meal, onSwap, swapping, onFeedback, forceExpand }) {
  const [expanded, setExpanded] = useState(false)
  const [swapReason, setSwapReason] = useState('')
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
    <article className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
      {/* Collapsed view */}
      <div className="cursor-pointer" onClick={() => setExpanded(!expanded)}>
        {recipe.image_url && (
          <div className="h-40 overflow-hidden bg-gray-100">
            <img src={recipe.image_url} alt={recipe.title} className="w-full h-full object-cover" loading="lazy" />
          </div>
        )}
        <div className="p-4">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-xs font-medium text-green-700 uppercase tracking-wide">{DAY_NAMES[day] || day}</p>
                {is_fallback && <span className="text-xs bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded">Auto</span>}
              </div>
              <h3 className="font-semibold text-gray-900 mt-1">{recipe.title}</h3>
              <CrowdRating score={popularity_score} count={recipe.rating_count || 0} />
            </div>
            <div className="text-right shrink-0">
              <span className="text-sm text-gray-500">{recipe.cook_time_minutes} min</span>
              <p className="text-xs text-gray-400">{DIFFICULTY_LABELS[recipe.difficulty] || recipe.difficulty}</p>
            </div>
          </div>

          <div className="flex items-center justify-between mt-3">
            <div className="text-sm">
              <span className="text-gray-700 font-medium">ca {Math.round(estimated_cost)} kr</span>
              <span className="text-gray-400 ml-1">({pricePerPortion} kr/port)</span>
              {savings > 1 && <span className="text-green-600 ml-1 font-medium">-{Math.round(savings)} kr</span>}
            </div>
            <button className="text-sm text-green-700 font-medium">{isExpanded ? 'Dölj ▲' : 'Visa ▼'}</button>
          </div>
        </div>
      </div>

      {/* Expanded view */}
      {isExpanded && (
        <div className="border-t border-gray-100 p-4 bg-gray-50">
          {reasoning && <p className="text-sm text-gray-500 italic mb-3">{reasoning}</p>}

          {/* Nutrition */}
          <NutritionBadges nutrition={recipe.nutrition} />

          {mealprep_tip && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-2.5 mb-3 mt-2 text-xs text-blue-800">
              <span className="font-medium">Mealprep-tips:</span> {mealprep_tip}
            </div>
          )}

          {/* Offer matches with prices */}
          {offer_matches && offer_matches.length > 0 && (
            <div className="mb-3">
              <h4 className="text-xs font-medium text-gray-500 mb-1">Erbjudanden som används</h4>
              <div className="flex flex-wrap gap-1">
                {offer_matches.map((o, i) => (
                  <span key={i} className="inline-block bg-green-50 text-green-700 text-xs px-2 py-0.5 rounded-full border border-green-200">
                    {o.product_name} <span className="font-medium">{Math.round(o.offer_price)} {o.unit}</span>
                    {o.original_price && <span className="text-green-500 ml-1 line-through">{Math.round(o.original_price)}</span>}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Ingredients — kitchen-rounded */}
          <div className="mb-4">
            <h4 className="font-medium text-sm text-gray-900 mb-2">Ingredienser ({scaled_servings} portioner)</h4>
            <ul className="text-sm text-gray-700 space-y-1">
              {recipe.ingredients.map((ing, i) => {
                const scaledAmount = kitchenRound(ing.amount * scale, ing.unit)
                return (
                  <li key={i} className="flex items-start gap-1.5">
                    <span className="text-gray-400 mt-0.5">-</span>
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
              Se originalrecept på {recipe.source || 'ica.se'} →
            </a>
          )}

          {/* Feedback */}
          <div className="flex items-center gap-3 mb-4">
            <span className="text-xs text-gray-500">Vad tyckte du?</span>
            {['liked', 'disliked'].map(action => (
              <button key={action} onClick={(e) => { e.stopPropagation(); handleFeedback(action) }}
                className={`px-3 py-1 rounded-full text-xs border transition-colors ${
                  feedback === action
                    ? action === 'liked' ? 'bg-green-100 text-green-700 border-green-300' : 'bg-red-100 text-red-700 border-red-300'
                    : 'border-gray-200 text-gray-500 hover:border-gray-400'
                }`}>
                {action === 'liked' ? 'Bra val' : 'Inte för mig'}
              </button>
            ))}
          </div>

          {/* Swap */}
          <div className="flex gap-2">
            <select value={swapReason} onChange={e => setSwapReason(e.target.value)}
              className="flex-1 py-2 px-3 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-green-700">
              {SWAP_REASONS.map(r => <option key={r.label} value={r.value}>{r.label}</option>)}
            </select>
            <button onClick={(e) => { e.stopPropagation(); onSwap(day, swapReason) }}
              disabled={swapping === day}
              className="py-2 px-4 text-sm border border-gray-300 rounded-lg hover:border-green-700 hover:text-green-700 disabled:opacity-50 transition-colors whitespace-nowrap">
              {swapping === day ? (
                <span className="flex items-center gap-1.5">
                  <span className="w-3.5 h-3.5 border-2 border-gray-300 border-t-green-700 rounded-full animate-spin" />
                  Byter...
                </span>
              ) : 'Byt recept'}
            </button>
          </div>
        </div>
      )}
    </article>
  )
}
