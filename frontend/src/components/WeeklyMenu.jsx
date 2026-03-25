import RecipeCard from './RecipeCard'
import SavingsBanner from './SavingsBanner'

export default function WeeklyMenu({ menu, onSwap, swapping, onShowShopping, onBack, onRegenerate, onFeedback, expandAll, setExpandAll }) {
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

      <div className="mt-8 text-center">
        <button onClick={onRegenerate} className="text-sm transition-colors" style={{ color: 'var(--text-muted)' }}>
          Generera ny meny
        </button>
      </div>
    </section>
  )
}
