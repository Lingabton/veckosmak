export default function SavingsBanner({ menu }) {
  if (!menu) return null

  const { total_savings, savings_percentage, total_cost, total_cost_without_offers,
    budget_exceeded, budget_exceeded_by, confirmed_savings, estimated_savings } = menu

  return (
    <div className="space-y-3 mb-6">
      {/* Budget warning */}
      {budget_exceeded && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
          <p className="text-amber-800 font-semibold">
            Menyn överskrider din budget med {Math.round(budget_exceeded_by)} kr
          </p>
          <p className="text-amber-600 text-sm mt-0.5">
            Prova att byta ut dyrare recept eller öka budgeten.
          </p>
        </div>
      )}

      {/* Savings */}
      <div className="bg-green-50 border border-green-200 rounded-xl p-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <p className="text-green-800 font-semibold text-lg">
              Du sparar ca {Math.round(total_savings)} kr ({Math.round(savings_percentage)}%)
            </p>
            <p className="text-green-600 text-sm">
              Uppskattat: {Math.round(total_cost)} kr
              <span className="text-green-500"> (ordinarie ~{Math.round(total_cost_without_offers)} kr)</span>
            </p>
          </div>
          <div className="text-3xl font-bold text-green-700">
            -{Math.round(total_savings)} kr
          </div>
        </div>
        {(confirmed_savings > 0 || estimated_savings > 0) && (
          <div className="flex gap-4 mt-2 text-xs text-green-600">
            {confirmed_savings > 0 && (
              <span>Bekräftad besparing: {Math.round(confirmed_savings)} kr</span>
            )}
            {estimated_savings > 0 && (
              <span className="text-green-400">Uppskattad: ~{Math.round(estimated_savings)} kr</span>
            )}
          </div>
        )}
        <p className="text-xs text-green-500 mt-2">
          Priserna är uppskattade. Faktiskt pris kan variera.
        </p>
      </div>
    </div>
  )
}
