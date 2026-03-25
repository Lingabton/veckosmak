export default function SavingsBanner({ menu }) {
  if (!menu) return null
  const { total_savings, savings_percentage, total_cost, budget_exceeded, budget_exceeded_by } = menu

  return (
    <div className="space-y-2 mb-6">
      {budget_exceeded && (
        <div className="rounded-xl px-4 py-3 text-sm" style={{ backgroundColor: '#fffbeb', border: '1px solid #fde68a', color: '#92400e' }}>
          Menyn överskrider budgeten med <strong>{Math.round(budget_exceeded_by)} kr</strong> — byt ut dyrare recept.
        </div>
      )}
      <div className="rounded-xl px-4 py-3 flex items-center justify-between" style={{ backgroundColor: 'var(--green-soft)', border: '1px solid #c6e7d0' }}>
        <div>
          <span className="font-semibold" style={{ color: 'var(--green-deep)' }}>
            {Math.round(total_cost)} kr uppskattad vecka
          </span>
          {total_savings > 0 && (
            <span className="text-sm ml-2" style={{ color: 'var(--green)' }}>
              sparar ~{Math.round(total_savings)} kr ({Math.round(savings_percentage)}%)
            </span>
          )}
        </div>
        {total_savings > 0 && (
          <span className="text-xl font-bold" style={{ color: 'var(--accent)' }}>
            −{Math.round(total_savings)} kr
          </span>
        )}
      </div>
    </div>
  )
}
