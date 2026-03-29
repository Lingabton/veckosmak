export default function SavingsBanner({ menu }) {
  if (!menu) return null
  const { total_savings, savings_percentage, total_cost, budget_exceeded, budget_exceeded_by, offers_note } = menu
  const budget = menu.preferences?.budget_per_week
  const underBudget = budget && total_cost <= budget

  return (
    <div className="space-y-2 mb-6">
      {offers_note && (
        <div className="card p-3 text-sm" style={{background:'#fffbeb',borderColor:'#fde68a',color:'#92400e'}}>
          {offers_note}
        </div>
      )}
      {budget_exceeded && (
        <div className="card p-3 text-sm" style={{background:'#fffbeb',borderColor:'#fde68a',color:'#92400e'}}>
          Menyn överskrider budgeten med <b>{Math.round(budget_exceeded_by)} kr</b> — byt ut dyrare recept.
        </div>
      )}
      <div className="rounded-2xl px-5 py-4" style={{background:'var(--color-brand-dark)', color:'white'}}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-wider font-medium" style={{opacity:0.6}}>Uppskattad veckokostnad</p>
            <p className="font-display text-2xl font-bold mt-0.5">{Math.round(total_cost)} kr</p>
          </div>
          {total_savings > 0 && (
            <div className="text-right">
              <p className="text-xs uppercase tracking-wider font-medium" style={{opacity:0.6}}>Du sparar</p>
              <p className="font-display text-2xl font-bold mt-0.5" style={{color:'#a7f3d0'}}>
                −{Math.round(total_savings)} kr
              </p>
              <p className="text-xs font-medium" style={{opacity:0.7}}>{Math.round(savings_percentage)}% billigare</p>
            </div>
          )}
          {total_savings === 0 && (
            <div className="text-right text-xs" style={{opacity:0.6}}>
              baserad på<br/>receptkvalitet
            </div>
          )}
        </div>
        {budget && (
          <div className="mt-3 pt-3" style={{borderTop:'1px solid rgba(255,255,255,0.15)'}}>
            <div className="flex items-center justify-between text-xs">
              <span style={{opacity:0.7}}>Budget: {budget} kr</span>
              {underBudget && (
                <span className="font-semibold" style={{color:'#a7f3d0'}}>
                  {Math.round(budget - total_cost)} kr under budget
                </span>
              )}
            </div>
            <div className="w-full rounded-full h-1.5 mt-1.5" style={{background:'rgba(255,255,255,0.2)'}}>
              <div className="h-1.5 rounded-full transition-all" style={{
                width: `${Math.min(100, (total_cost / budget) * 100)}%`,
                background: underBudget ? '#a7f3d0' : 'var(--color-accent)',
              }} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
