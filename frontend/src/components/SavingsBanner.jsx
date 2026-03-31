export default function SavingsBanner({ menu }) {
  if (!menu) return null
  const { total_savings, savings_percentage, total_cost, budget_exceeded, budget_exceeded_by, offers_note } = menu
  const budget = menu.preferences?.budget_per_week
  const underBudget = budget && total_cost <= budget
  const budgetProgress = budget ? Math.min(100, (total_cost / budget) * 100) : 0

  return (
    <div className="mb-6 fade-up">
      {budget_exceeded && (
        <div className="flex items-center gap-2 text-sm px-4 py-2.5 rounded-xl mb-3"
          style={{ background: '#fffbeb', border: '1px solid #fde68a', color: '#92400e' }}>
          <span style={{ fontSize: '15px' }}>!</span>
          Menyn överskrider budgeten med <b>{Math.round(budget_exceeded_by)} kr</b> — byt ut dyrare recept.
        </div>
      )}

      {/* Glass morphism card */}
      <div className="rounded-2xl px-6 py-5 relative overflow-hidden" style={{
        background: 'linear-gradient(135deg, rgba(232,245,233,0.7) 0%, rgba(255,255,255,0.8) 50%, rgba(232,245,233,0.5) 100%)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: '1px solid rgba(26,92,53,0.12)',
        boxShadow: '0 4px 24px rgba(26,92,53,0.06), inset 0 1px 0 rgba(255,255,255,0.6)',
      }}>
        {/* Subtle decorative element */}
        <div className="absolute -top-20 -right-20 w-40 h-40 rounded-full" style={{
          background: 'radial-gradient(circle, rgba(26,92,53,0.06) 0%, transparent 70%)',
          pointerEvents: 'none',
        }} />

        {/* Split layout */}
        <div className="flex items-start justify-between relative">
          {/* Left: Total cost */}
          <div>
            <p className="text-[11px] uppercase tracking-widest font-medium mb-1" style={{ color: 'var(--color-text-muted)' }}>
              Uppskattad veckokostnad
            </p>
            <p className="font-display text-4xl font-bold" style={{ color: 'var(--color-text)', lineHeight: 1.1 }}>
              {Math.round(total_cost)}
              <span className="text-lg font-normal ml-1" style={{ color: 'var(--color-text-muted)' }}>kr</span>
            </p>
            {offers_note && (
              <p className="text-xs mt-2 max-w-xs" style={{ color: 'var(--color-text-muted)' }}>
                {offers_note}
              </p>
            )}
          </div>

          {/* Right: Savings */}
          {total_savings > 0 ? (
            <div className="text-right">
              <p className="text-[11px] uppercase tracking-widest font-medium mb-1" style={{ color: 'var(--color-text-muted)' }}>
                Beräknad besparing
              </p>
              <p className="font-display text-3xl font-bold" style={{
                background: 'linear-gradient(135deg, #16a34a, #059669)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
                lineHeight: 1.1,
              }}>
                {Math.round(total_savings)} kr
              </p>
              <p className="text-xs font-semibold mt-1 px-2 py-0.5 rounded-full inline-block" style={{
                background: 'rgba(22,163,74,0.08)',
                color: '#16a34a',
              }}>
                {Math.round(savings_percentage)} % billigare
              </p>
              <p className="text-[10px] mt-1.5" style={{color:'var(--color-text-muted)'}}>jämfört med ordinarie pris</p>
            </div>
          ) : (
            <div className="text-right">
              <p className="text-xs leading-relaxed" style={{ color: 'var(--color-text-muted)' }}>
                Optimerad efter<br />receptkvalitet
              </p>
            </div>
          )}
        </div>

        {/* Budget progress bar */}
        {budget && (
          <div className="mt-5">
            <div className="flex items-center justify-between text-xs mb-2">
              <span style={{ color: 'var(--color-text-muted)' }}>Budget: {budget} kr</span>
              {underBudget && (
                <span className="font-semibold" style={{
                  background: 'linear-gradient(135deg, #16a34a, #059669)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text',
                }}>
                  {Math.round(budget - total_cost)} kr under budget
                </span>
              )}
            </div>
            <div className="relative w-full h-1 rounded-full" style={{ background: 'rgba(26,92,53,0.08)' }}>
              <div className="h-1 rounded-full transition-all duration-700 ease-out" style={{
                width: `${budgetProgress}%`,
                background: underBudget
                  ? 'linear-gradient(90deg, #16a34a, #059669)'
                  : 'linear-gradient(90deg, var(--color-accent), #e03131)',
              }} />
              {/* Marker dot */}
              <div className="absolute top-1/2 -translate-y-1/2 transition-all duration-700 ease-out" style={{
                left: `${budgetProgress}%`,
                transform: `translateX(-50%) translateY(-50%)`,
              }}>
                <div className="w-3 h-3 rounded-full border-2" style={{
                  background: 'var(--color-surface)',
                  borderColor: underBudget ? '#16a34a' : 'var(--color-accent)',
                  boxShadow: `0 0 0 3px ${underBudget ? 'rgba(22,163,74,0.15)' : 'rgba(212,85,42,0.15)'}`,
                }} />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
