export default function SavingsBanner({ menu }) {
  if (!menu) return null
  const { total_savings, savings_percentage, total_cost, budget_exceeded, budget_exceeded_by } = menu

  return (
    <div className="space-y-2 mb-5">
      {budget_exceeded && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex items-center gap-2 text-sm">
          <span className="text-lg">⚠️</span>
          <p className="text-amber-800">
            Menyn överskrider budgeten med <strong>{Math.round(budget_exceeded_by)} kr</strong>. Byt ut dyrare recept.
          </p>
        </div>
      )}
      <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-3 flex items-center justify-between">
        <div>
          <span className="text-green-800 font-semibold">
            Uppskattat: {Math.round(total_cost)} kr
          </span>
          {total_savings > 0 && (
            <span className="text-green-600 text-sm ml-2">
              sparar ~{Math.round(total_savings)} kr ({Math.round(savings_percentage)}%)
            </span>
          )}
        </div>
        {total_savings > 0 && (
          <span className="text-2xl font-bold text-green-700" style={{ color: 'var(--accent)' }}>
            -{Math.round(total_savings)} kr
          </span>
        )}
      </div>
    </div>
  )
}
