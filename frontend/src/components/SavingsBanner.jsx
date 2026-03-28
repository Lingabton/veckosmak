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
      <div className="card px-4 py-3" style={{background:'var(--color-brand-light)'}}>
        <div className="flex items-center justify-between">
          <div>
            <span className="font-bold" style={{color:'var(--color-brand-dark)'}}>
              Uppskattad veckokostnad: {Math.round(total_cost)} kr
            </span>
            {total_savings > 0 ? (
              <span className="text-sm ml-2" style={{color:'var(--color-brand)'}}>
                sparar ~{Math.round(total_savings)} kr ({Math.round(savings_percentage)}%)
              </span>
            ) : (
              <span className="text-sm ml-2" style={{color:'var(--color-text-muted)'}}>
                baserad på receptkvalitet
              </span>
            )}
          </div>
          {total_savings > 0 && <span className="text-xl font-bold" style={{color:'var(--color-accent)'}}>−{Math.round(total_savings)} kr</span>}
        </div>
        {budget && (
          <div className="mt-2 pt-2" style={{borderTop:'1px solid rgba(0,0,0,0.08)'}}>
            <div className="flex items-center justify-between text-xs">
              <span style={{color:'var(--color-brand)'}}>Budget: {budget} kr</span>
              {underBudget && (
                <span className="font-semibold" style={{color:'var(--color-brand-dark)'}}>
                  {Math.round(budget - total_cost)} kr under budget
                </span>
              )}
            </div>
            <div className="w-full rounded-full h-1.5 mt-1" style={{background:'rgba(0,0,0,0.1)'}}>
              <div className="h-1.5 rounded-full transition-all" style={{
                width: `${Math.min(100, (total_cost / budget) * 100)}%`,
                background: underBudget ? 'var(--color-brand-dark)' : 'var(--color-accent)',
              }} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
