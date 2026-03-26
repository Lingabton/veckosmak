export default function SavingsBanner({ menu }) {
  if (!menu) return null
  const { total_savings, savings_percentage, total_cost, budget_exceeded, budget_exceeded_by } = menu
  return (
    <div className="space-y-2 mb-6">
      {budget_exceeded && (
        <div className="card p-3 text-sm" style={{background:'#fffbeb',borderColor:'#fde68a',color:'#92400e'}}>
          Menyn överskrider budgeten med <b>{Math.round(budget_exceeded_by)} kr</b> — byt ut dyrare recept.
        </div>
      )}
      <div className="card px-4 py-3 flex items-center justify-between" style={{background:'var(--color-brand-light)'}}>
        <div>
          <span className="font-bold" style={{color:'var(--color-brand-dark)'}}>
            {Math.round(total_cost)} kr uppskattad vecka
          </span>
          {total_savings > 0 && (
            <span className="text-sm ml-2" style={{color:'var(--color-brand)'}}>
              sparar ~{Math.round(total_savings)} kr ({Math.round(savings_percentage)}%)
            </span>
          )}
        </div>
        {total_savings > 0 && <span className="text-2xl font-bold" style={{color:'var(--color-accent)'}}>−{Math.round(total_savings)} kr</span>}
      </div>
    </div>
  )
}
