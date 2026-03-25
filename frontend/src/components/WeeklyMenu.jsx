import RecipeCard from './RecipeCard'
import SavingsBanner from './SavingsBanner'

const STORE_NAMES = {
  'ica-maxi-1004097': 'ICA Maxi Boglundsängen, Örebro',
}

export default function WeeklyMenu({ menu, onSwap, swapping, onShowShopping, onBack, onRegenerate, onFeedback, expandAll, setExpandAll }) {
  if (!menu) return null

  const storeName = STORE_NAMES[menu.store_id] || menu.store_id

  return (
    <section aria-label="Veckomeny">
      <div className="flex items-center justify-between mb-4">
        <button onClick={onBack}
          className="text-sm text-gray-500 hover:text-green-700 transition-colors">
          ← Ändra inställningar
        </button>
        <button onClick={onShowShopping}
          className="text-sm font-medium text-green-700 hover:text-green-800 transition-colors">
          Visa inköpslista →
        </button>
      </div>

      <div className="mb-4">
        <h1 className="text-xl font-bold text-gray-900">Din veckomeny</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Vecka {menu.week_number}, {menu.year} — {storeName}
        </p>
      </div>

      <SavingsBanner menu={menu} />

      {/* Quick filters / actions */}
      <div className="flex items-center justify-between mb-4">
        <button onClick={() => setExpandAll(!expandAll)}
          className="text-xs text-gray-500 hover:text-green-700 transition-colors">
          {expandAll ? 'Dölj alla recept' : 'Visa alla recept'}
        </button>
        <span className="text-xs text-gray-400">
          {menu.meals.length} middagar
        </span>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {menu.meals.map(meal => (
          <RecipeCard
            key={meal.day}
            meal={meal}
            onSwap={onSwap}
            swapping={swapping}
            onFeedback={onFeedback}
            forceExpand={expandAll}
          />
        ))}
      </div>

      <div className="mt-6 text-center">
        <button onClick={onRegenerate}
          className="text-sm text-gray-500 hover:text-green-700 transition-colors underline">
          Generera en helt ny meny
        </button>
      </div>
    </section>
  )
}
