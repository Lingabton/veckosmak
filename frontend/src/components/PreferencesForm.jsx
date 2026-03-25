import { useState } from 'react'

const DIET_OPTIONS = [
  { value: 'vegetarian', label: 'Vegetarisk' },
  { value: 'vegan', label: 'Vegansk' },
  { value: 'glutenfree', label: 'Glutenfri' },
  { value: 'dairyfree', label: 'Mjölkfri' },
  { value: 'lactosefree', label: 'Laktosfri' },
  { value: 'porkfree', label: 'Fläskfri' },
]

const LIFESTYLE_OPTIONS = [
  { value: 'avoid_processed', label: 'Undvik processad' },
  { value: 'prefer_healthy', label: 'Hälsosammare' },
  { value: 'prefer_highprotein', label: 'Proteinrikt' },
  { value: 'prefer_lowcarb', label: 'Lågkolhydrat' },
  { value: 'prefer_sustainable', label: 'Klimatsmart' },
  { value: 'prefer_seasonal', label: 'Säsong' },
  { value: 'reduce_waste', label: 'Minska svinn' },
]

const COMMON_DISLIKES = [
  'räkor', 'selleri', 'koriander', 'svamp', 'oliver',
  'paprika', 'chili', 'ingefära', 'kokos', 'anjovis',
]

const ALL_DAYS = [
  { value: 'monday', label: 'Mån' }, { value: 'tuesday', label: 'Tis' },
  { value: 'wednesday', label: 'Ons' }, { value: 'thursday', label: 'Tor' },
  { value: 'friday', label: 'Fre' }, { value: 'saturday', label: 'Lör' },
  { value: 'sunday', label: 'Sön' },
]

function Pill({ active, onClick, children, color = 'green' }) {
  const styles = {
    green: active
      ? { backgroundColor: 'var(--green)', color: 'white', borderColor: 'var(--green)' }
      : { borderColor: 'var(--border)' },
    red: active
      ? { backgroundColor: '#fef2f2', color: '#b91c1c', borderColor: '#fecaca' }
      : { backgroundColor: 'var(--bg)', borderColor: 'var(--border)' },
  }
  return (
    <button onClick={onClick} style={styles[color]}
      className="px-3.5 py-2 rounded-full text-sm border transition-all hover:shadow-sm">
      {children}
    </button>
  )
}

function Stepper({ value, onChange, min, max, label }) {
  return (
    <div>
      <label className="block text-sm font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>{label}</label>
      <div className="flex items-center gap-3">
        <button onClick={() => onChange(Math.max(min, value - 1))}
          className="w-11 h-11 rounded-full border text-lg font-medium transition-colors hover:shadow-sm"
          style={{ borderColor: 'var(--border)' }}>−</button>
        <span className="text-xl font-semibold w-12 text-center">{value}</span>
        <button onClick={() => onChange(Math.min(max, value + 1))}
          className="w-11 h-11 rounded-full border text-lg font-medium transition-colors hover:shadow-sm"
          style={{ borderColor: 'var(--border)' }}>+</button>
      </div>
    </div>
  )
}

export default function PreferencesForm({ preferences, setPreferences, onGenerate, onGenerateDirect, loading, isReturning }) {
  const [showMore, setShowMore] = useState(false)
  const update = (key, value) => setPreferences({ ...preferences, [key]: value })
  const toggleList = (key, value) => {
    const c = preferences[key] || []
    update(key, c.includes(value) ? c.filter(d => d !== value) : [...c, value])
  }
  const toggleDay = (day) => {
    const c = preferences.selected_days || []
    const next = c.includes(day) ? c.filter(d => d !== day) : [...c, day]
    setPreferences({ ...preferences, selected_days: next, num_dinners: next.length || preferences.num_dinners })
  }
  const useSpecificDays = (preferences.selected_days || []).length > 0
  const hasAdvanced = preferences.dietary_restrictions?.length > 0 ||
    (preferences.lifestyle_preferences || []).length > 0 ||
    preferences.disliked_ingredients?.length > 0 ||
    preferences.has_children || preferences.budget_per_week !== null

  return (
    <div className="animate-fade-in">
      {/* Hero */}
      <section className="text-center mb-10">
        <h1 className="text-3xl font-bold tracking-tight mb-3" style={{ color: 'var(--text)' }}>
          Middagar som sparar dig pengar
        </h1>
        <p className="text-base leading-relaxed max-w-md mx-auto" style={{ color: 'var(--text-secondary)' }}>
          Vi matchar veckans bästa erbjudanden mot populära recept
          och skapar en komplett veckomeny med inköpslista.
        </p>
        <div className="flex items-center justify-center gap-6 mt-5 text-sm" style={{ color: 'var(--text-muted)' }}>
          <span>600+ recept</span>
          <span style={{ color: 'var(--border)' }}>·</span>
          <span>Spara 200–400 kr/v</span>
          <span style={{ color: 'var(--border)' }}>·</span>
          <span>Helt gratis</span>
        </div>
      </section>

      {/* How it works */}
      <section className="grid grid-cols-3 gap-4 mb-10">
        {[
          ['1', 'Ange preferenser', 'Hushåll, kostval, budget'],
          ['2', 'Välj erbjudanden', 'Eller låt oss välja'],
          ['3', 'Få din veckomeny', 'Recept + inköpslista'],
        ].map(([n, title, desc]) => (
          <div key={n} className="text-center">
            <div className="w-8 h-8 rounded-full flex items-center justify-center mx-auto mb-2 text-sm font-semibold text-white"
              style={{ backgroundColor: 'var(--green)' }}>{n}</div>
            <p className="text-sm font-medium">{title}</p>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{desc}</p>
          </div>
        ))}
      </section>

      {/* Returning user shortcut */}
      {isReturning && (
        <button onClick={onGenerateDirect} disabled={loading}
          className="w-full mb-5 py-3.5 rounded-xl text-white font-semibold text-base transition-colors animate-fade-in"
          style={{ backgroundColor: 'var(--accent)' }}>
          Skapa meny med mina inställningar
        </button>
      )}

      {/* Store */}
      <p className="text-xs mb-4" style={{ color: 'var(--text-muted)' }}>
        Erbjudanden från ICA Maxi Boglundsängen, Örebro
      </p>

      {/* Form */}
      <div className="rounded-2xl p-6 border" style={{ backgroundColor: 'var(--surface)', borderColor: 'var(--border)' }}>
        <div className="space-y-6">
          {/* Core */}
          <div className="grid grid-cols-2 gap-6">
            <Stepper value={preferences.household_size} onChange={v => update('household_size', v)} min={1} max={8} label="Antal personer" />
            {!useSpecificDays && (
              <Stepper value={preferences.num_dinners} onChange={v => update('num_dinners', v)} min={1} max={7} label="Middagar/vecka" />
            )}
          </div>

          {/* Advanced toggle */}
          <button onClick={() => setShowMore(!showMore)}
            className="w-full text-sm py-1.5 transition-colors" style={{ color: 'var(--text-muted)' }}>
            {showMore ? 'Dölj inställningar' : `Fler inställningar${hasAdvanced ? ' (aktiva)' : ''}`}
            <span className="ml-1">{showMore ? '▲' : '▼'}</span>
          </button>

          {showMore && (
            <div className="space-y-6 pt-4 animate-expand" style={{ borderTop: '1px solid var(--border-light)' }}>
              {/* Children */}
              <label className="flex items-center gap-3 cursor-pointer text-sm">
                <input type="checkbox" checked={preferences.has_children}
                  onChange={e => update('has_children', e.target.checked)}
                  className="w-5 h-5 rounded accent-green-700" />
                <span>Hushållet har barn</span>
              </label>

              {/* Days */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>Specifika dagar</label>
                  <input type="checkbox" checked={useSpecificDays}
                    onChange={e => {
                      if (!e.target.checked) setPreferences({ ...preferences, selected_days: [] })
                      else setPreferences({ ...preferences, selected_days: ALL_DAYS.slice(0, preferences.num_dinners).map(d => d.value) })
                    }}
                    className="w-5 h-5 rounded accent-green-700" />
                </div>
                {useSpecificDays && (
                  <div className="flex gap-1.5">
                    {ALL_DAYS.map(d => (
                      <button key={d.value} onClick={() => toggleDay(d.value)}
                        className="w-11 h-11 rounded-full text-xs font-medium border transition-all"
                        style={(preferences.selected_days || []).includes(d.value)
                          ? { backgroundColor: 'var(--green)', color: 'white', borderColor: 'var(--green)' }
                          : { borderColor: 'var(--border)' }}>
                        {d.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Budget */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>Veckobudget</label>
                  <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                    <span>{preferences.budget_per_week ? `${preferences.budget_per_week} kr` : 'Av'}</span>
                    <input type="checkbox" checked={preferences.budget_per_week !== null}
                      onChange={e => update('budget_per_week', e.target.checked ? 1000 : null)}
                      className="w-5 h-5 rounded accent-green-700" />
                  </div>
                </div>
                {preferences.budget_per_week !== null && (
                  <input type="range" min="300" max="2000" step="100" value={preferences.budget_per_week}
                    onChange={e => update('budget_per_week', Number(e.target.value))}
                    className="w-full h-1.5 rounded-lg appearance-none cursor-pointer accent-green-700"
                    style={{ backgroundColor: 'var(--border)' }} />
                )}
              </div>

              {/* Diet */}
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>Kostval</label>
                <div className="flex gap-2 flex-wrap">
                  {DIET_OPTIONS.map(opt => (
                    <Pill key={opt.value} active={preferences.dietary_restrictions.includes(opt.value)}
                      onClick={() => toggleList('dietary_restrictions', opt.value)}>{opt.label}</Pill>
                  ))}
                </div>
              </div>

              {/* Lifestyle */}
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>Livsstil</label>
                <div className="flex gap-2 flex-wrap">
                  {LIFESTYLE_OPTIONS.map(opt => (
                    <Pill key={opt.value} active={(preferences.lifestyle_preferences || []).includes(opt.value)}
                      onClick={() => toggleList('lifestyle_preferences', opt.value)}>{opt.label}</Pill>
                  ))}
                </div>
              </div>

              {/* Disliked */}
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>Undvik</label>
                <div className="flex gap-1.5 flex-wrap mb-2">
                  {COMMON_DISLIKES.map(ing => (
                    <Pill key={ing} active={preferences.disliked_ingredients.includes(ing)}
                      onClick={() => toggleList('disliked_ingredients', ing)} color="red">{ing}</Pill>
                  ))}
                </div>
                <input type="text" placeholder="Övriga, kommaseparerat"
                  value={preferences.disliked_ingredients.filter(d => !COMMON_DISLIKES.includes(d)).join(', ')}
                  onChange={e => {
                    const custom = e.target.value ? e.target.value.split(',').map(s => s.trim()).filter(Boolean) : []
                    const fromButtons = preferences.disliked_ingredients.filter(d => COMMON_DISLIKES.includes(d))
                    update('disliked_ingredients', [...fromButtons, ...custom])
                  }}
                  className="w-full px-3.5 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-700 focus:border-transparent"
                  style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg)' }} />
              </div>
            </div>
          )}

          {/* CTA */}
          <button onClick={onGenerate} disabled={loading}
            className="w-full py-3.5 rounded-xl text-white font-semibold text-base transition-colors disabled:opacity-50"
            style={{ backgroundColor: 'var(--accent)' }}>
            {loading ? 'Hämtar erbjudanden...' : 'Skapa min veckomeny'}
          </button>
        </div>
      </div>

      {/* SEO */}
      <section className="mt-12 space-y-6 text-sm" style={{ color: 'var(--text-muted)' }}>
        <div>
          <h2 className="text-base font-semibold mb-1.5" style={{ color: 'var(--text)' }}>Menyplanering som sparar pengar</h2>
          <p className="leading-relaxed">Med Veckosmak får du en veckomeny baserad på erbjudanden från din lokala matbutik. Vår AI matchar recept mot kampanjer så du får maximalt med smak för pengarna.</p>
        </div>
        <div>
          <h2 className="text-base font-semibold mb-1.5" style={{ color: 'var(--text)' }}>Så fungerar det</h2>
          <p className="leading-relaxed">Varje vecka hämtar vi erbjudanden från ICA Maxi och matchar dem mot 600+ recept med betyg. Du får en skräddarsydd veckomeny med näringsinfo och inköpslista.</p>
        </div>
      </section>
    </div>
  )
}
