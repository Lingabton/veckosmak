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
  { value: 'prefer_organic', label: 'Ekologiskt' },
  { value: 'reduce_waste', label: 'Minska svinn' },
]

const COMMON_DISLIKES = [
  'räkor', 'selleri', 'koriander', 'svamp', 'oliver', 'aubergine',
  'paprika', 'chili', 'ingefära', 'kokos', 'anjovis', 'kapris',
]

const ALL_DAYS = [
  { value: 'monday', label: 'Mån' }, { value: 'tuesday', label: 'Tis' },
  { value: 'wednesday', label: 'Ons' }, { value: 'thursday', label: 'Tor' },
  { value: 'friday', label: 'Fre' }, { value: 'saturday', label: 'Lör' },
  { value: 'sunday', label: 'Sön' },
]

const TIME_MIX_PRESETS = [
  { label: 'Alla tider', value: null },
  { label: '≤30 min', value: { allQuick: true } },
  { label: 'Blandning', value: { mix: true } },
  { label: '≤45 min', value: { max: 45 } },
]

export default function PreferencesForm({ preferences, setPreferences, onGenerate, loading }) {
  const [showMore, setShowMore] = useState(false)

  const update = (key, value) => setPreferences({ ...preferences, [key]: value })

  const toggleList = (key, value) => {
    const current = preferences[key] || []
    const next = current.includes(value) ? current.filter(d => d !== value) : [...current, value]
    update(key, next)
  }

  const toggleDay = (day) => {
    const current = preferences.selected_days || []
    const next = current.includes(day) ? current.filter(d => d !== day) : [...current, day]
    setPreferences({ ...preferences, selected_days: next, num_dinners: next.length || preferences.num_dinners })
  }

  const useSpecificDays = (preferences.selected_days || []).length > 0
  const hasAdvancedPrefs = (preferences.dietary_restrictions?.length > 0) ||
    (preferences.lifestyle_preferences?.length > 0) ||
    (preferences.disliked_ingredients?.length > 0) ||
    preferences.has_children || preferences.time_mix || preferences.max_cook_time ||
    preferences.budget_per_week !== null

  const setTimeMixPreset = (preset) => {
    if (!preset) {
      setPreferences({ ...preferences, max_cook_time: null, time_mix: null })
    } else if (preset.allQuick) {
      setPreferences({ ...preferences, max_cook_time: 30, time_mix: null })
    } else if (preset.mix) {
      const quick = Math.ceil(preferences.num_dinners / 2)
      setPreferences({ ...preferences, max_cook_time: null, time_mix: { quick_count: quick, medium_count: 0, slow_count: preferences.num_dinners - quick } })
    } else if (preset.max) {
      setPreferences({ ...preferences, max_cook_time: preset.max, time_mix: null })
    }
  }

  const timeMixMode = preferences.time_mix ? 'mix' : preferences.max_cook_time ? 'max' : 'none'

  return (
    <div>
      {/* Hero */}
      <section className="text-center mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Veckomeny baserad på veckans erbjudanden</h1>
        <p className="text-gray-600 leading-relaxed max-w-lg mx-auto">
          Spara pengar på maten varje vecka. Veckosmak matchar recept mot din butiks erbjudanden
          — goda middagar till lägre pris.
        </p>
      </section>

      {/* How it works */}
      <section className="grid grid-cols-3 gap-3 mb-8">
        {[
          ['1', 'Välj preferenser', 'Storlek & kostval'],
          ['2', 'Välj bästa köp', 'Eller bli överraskad'],
          ['3', 'Få meny + spara', 'Recept & inköpslista'],
        ].map(([n, title, desc]) => (
          <div key={n} className="text-center p-3">
            <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-2">
              <span className="text-green-700 font-bold text-sm">{n}</span>
            </div>
            <h3 className="text-xs font-medium text-gray-900">{title}</h3>
            <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
          </div>
        ))}
      </section>

      {/* Store */}
      <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 mb-6 text-sm text-green-800">
        Erbjudanden från <strong>ICA Maxi Boglundsängen, Örebro</strong>
      </div>

      {/* Form */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Skapa din veckomeny</h2>

        <div className="space-y-5">
          {/* Core: Household + Dinners — always visible */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Hushåll</label>
              <div className="flex items-center gap-2">
                <button onClick={() => update('household_size', Math.max(1, preferences.household_size - 1))}
                  className="w-9 h-9 rounded-full border border-gray-300 font-bold hover:border-green-700 hover:text-green-700 transition-colors">-</button>
                <span className="text-lg font-semibold w-16 text-center">{preferences.household_size} pers</span>
                <button onClick={() => update('household_size', Math.min(8, preferences.household_size + 1))}
                  className="w-9 h-9 rounded-full border border-gray-300 font-bold hover:border-green-700 hover:text-green-700 transition-colors">+</button>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Middagar/vecka</label>
              {!useSpecificDays && (
                <div className="flex items-center gap-2">
                  <button onClick={() => update('num_dinners', Math.max(1, preferences.num_dinners - 1))}
                    className="w-9 h-9 rounded-full border border-gray-300 font-bold hover:border-green-700 hover:text-green-700 transition-colors">-</button>
                  <span className="text-lg font-semibold w-16 text-center">{preferences.num_dinners} st</span>
                  <button onClick={() => update('num_dinners', Math.min(7, preferences.num_dinners + 1))}
                    className="w-9 h-9 rounded-full border border-gray-300 font-bold hover:border-green-700 hover:text-green-700 transition-colors">+</button>
                </div>
              )}
              {useSpecificDays && (
                <span className="text-lg font-semibold">{(preferences.selected_days || []).length} dagar</span>
              )}
            </div>
          </div>

          {/* Expand/collapse advanced settings */}
          <button onClick={() => setShowMore(!showMore)}
            className="w-full text-sm text-gray-500 hover:text-green-700 transition-colors py-1 flex items-center justify-center gap-1">
            {showMore ? 'Dölj inställningar ▲' : `Fler inställningar ▼${hasAdvancedPrefs ? ' (aktiva)' : ''}`}
          </button>

          {showMore && (
            <div className="space-y-5 pt-2 border-t border-gray-100">
              {/* Children */}
              <label className="flex items-center gap-3 cursor-pointer">
                <input type="checkbox" checked={preferences.has_children}
                  onChange={e => update('has_children', e.target.checked)}
                  className="w-5 h-5 rounded border-gray-300 text-green-700 focus:ring-green-700" />
                <span className="text-sm text-gray-700">Hushållet har barn</span>
              </label>

              {/* Specific days */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-gray-700">Specifika dagar</label>
                  <input type="checkbox" checked={useSpecificDays}
                    onChange={e => {
                      if (!e.target.checked) setPreferences({ ...preferences, selected_days: [] })
                      else setPreferences({ ...preferences, selected_days: ALL_DAYS.slice(0, preferences.num_dinners).map(d => d.value) })
                    }}
                    className="w-4 h-4 rounded border-gray-300 text-green-700" />
                </div>
                {useSpecificDays && (
                  <div className="flex gap-1.5">
                    {ALL_DAYS.map(d => (
                      <button key={d.value} onClick={() => toggleDay(d.value)}
                        className={`w-10 h-10 rounded-full text-xs font-medium border transition-colors ${
                          (preferences.selected_days || []).includes(d.value)
                            ? 'bg-green-700 text-white border-green-700' : 'border-gray-300 hover:border-green-700'
                        }`}>{d.label}</button>
                    ))}
                  </div>
                )}
              </div>

              {/* Budget */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-gray-700">Budget</label>
                  <label className="flex items-center gap-2 cursor-pointer text-xs text-gray-500">
                    {preferences.budget_per_week ? `${preferences.budget_per_week} kr` : 'Av'}
                    <input type="checkbox" checked={preferences.budget_per_week !== null}
                      onChange={e => update('budget_per_week', e.target.checked ? 1000 : null)}
                      className="w-4 h-4 rounded border-gray-300 text-green-700" />
                  </label>
                </div>
                {preferences.budget_per_week !== null && (
                  <input type="range" min="300" max="2000" step="100" value={preferences.budget_per_week}
                    onChange={e => update('budget_per_week', Number(e.target.value))}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-green-700" />
                )}
              </div>

              {/* Time mix */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Tillagningstid</label>
                <div className="flex gap-2 flex-wrap">
                  {TIME_MIX_PRESETS.map((preset, i) => {
                    const isActive = (!preset.value && timeMixMode === 'none')
                      || (preset.value?.allQuick && preferences.max_cook_time === 30 && !preferences.time_mix)
                      || (preset.value?.mix && !!preferences.time_mix)
                      || (preset.value?.max && preferences.max_cook_time === preset.value.max)
                    return (
                      <button key={i} onClick={() => setTimeMixPreset(preset.value)}
                        className={`px-3 py-1.5 rounded-full text-sm border transition-colors ${
                          isActive ? 'bg-green-700 text-white border-green-700' : 'border-gray-300 hover:border-green-700'
                        }`}>{preset.label}</button>
                    )
                  })}
                </div>
                {preferences.time_mix && (
                  <div className="mt-2 flex gap-4 text-sm">
                    <div>
                      <span className="text-xs text-gray-500">Snabba ≤30</span>
                      <div className="flex items-center gap-1.5 mt-1">
                        <button onClick={() => setPreferences({...preferences, time_mix: {...preferences.time_mix, quick_count: Math.max(0, preferences.time_mix.quick_count-1), slow_count: Math.min(preferences.num_dinners, preferences.time_mix.slow_count+1)}})}
                          className="w-7 h-7 rounded-full border text-xs font-bold">-</button>
                        <span className="font-semibold w-3 text-center">{preferences.time_mix.quick_count}</span>
                        <button onClick={() => setPreferences({...preferences, time_mix: {...preferences.time_mix, quick_count: Math.min(preferences.num_dinners, preferences.time_mix.quick_count+1), slow_count: Math.max(0, preferences.time_mix.slow_count-1)}})}
                          className="w-7 h-7 rounded-full border text-xs font-bold">+</button>
                      </div>
                    </div>
                    <div>
                      <span className="text-xs text-gray-500">Längre 46+</span>
                      <div className="flex items-center gap-1.5 mt-1">
                        <button onClick={() => setPreferences({...preferences, time_mix: {...preferences.time_mix, slow_count: Math.max(0, preferences.time_mix.slow_count-1), quick_count: Math.min(preferences.num_dinners, preferences.time_mix.quick_count+1)}})}
                          className="w-7 h-7 rounded-full border text-xs font-bold">-</button>
                        <span className="font-semibold w-3 text-center">{preferences.time_mix.slow_count}</span>
                        <button onClick={() => setPreferences({...preferences, time_mix: {...preferences.time_mix, slow_count: Math.min(preferences.num_dinners, preferences.time_mix.slow_count+1), quick_count: Math.max(0, preferences.time_mix.quick_count-1)}})}
                          className="w-7 h-7 rounded-full border text-xs font-bold">+</button>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Diet as pills */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Kostval</label>
                <div className="flex gap-2 flex-wrap">
                  {DIET_OPTIONS.map(opt => (
                    <button key={opt.value} onClick={() => toggleList('dietary_restrictions', opt.value)}
                      className={`px-3 py-1.5 rounded-full text-sm border transition-colors ${
                        preferences.dietary_restrictions.includes(opt.value)
                          ? 'bg-green-700 text-white border-green-700' : 'border-gray-300 hover:border-green-700'
                      }`}>{opt.label}</button>
                  ))}
                </div>
              </div>

              {/* Lifestyle as pills */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Livsstil</label>
                <div className="flex gap-2 flex-wrap">
                  {LIFESTYLE_OPTIONS.map(opt => (
                    <button key={opt.value} onClick={() => toggleList('lifestyle_preferences', opt.value)}
                      className={`px-3 py-1.5 rounded-full text-sm border transition-colors ${
                        (preferences.lifestyle_preferences || []).includes(opt.value)
                          ? 'bg-green-700 text-white border-green-700' : 'border-gray-300 hover:border-green-700'
                      }`}>{opt.label}</button>
                  ))}
                </div>
              </div>

              {/* Disliked */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Undvik ingredienser</label>
                <div className="flex gap-1.5 flex-wrap mb-2">
                  {COMMON_DISLIKES.map(ing => (
                    <button key={ing} onClick={() => toggleList('disliked_ingredients', ing)}
                      className={`px-2.5 py-1 rounded-full text-xs border transition-colors ${
                        preferences.disliked_ingredients.includes(ing)
                          ? 'bg-red-100 text-red-700 border-red-300' : 'bg-gray-50 text-gray-600 border-gray-200 hover:border-red-300'
                      }`}>{ing}</button>
                  ))}
                </div>
                <input type="text" placeholder="Övriga (kommaseparerat)"
                  value={preferences.disliked_ingredients.filter(d => !COMMON_DISLIKES.includes(d)).join(', ')}
                  onChange={e => {
                    const custom = e.target.value ? e.target.value.split(',').map(s => s.trim()).filter(Boolean) : []
                    const fromButtons = preferences.disliked_ingredients.filter(d => COMMON_DISLIKES.includes(d))
                    update('disliked_ingredients', [...fromButtons, ...custom])
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-700 focus:border-transparent" />
              </div>

              {/* Pantry / already have */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Jag har redan hemma</label>
                <p className="text-xs text-gray-400 mb-2">Varor som inte behöver hamna på inköpslistan</p>
                <input type="text" placeholder="T.ex. ris, pasta, olivolja (kommaseparerat)"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-700 focus:border-transparent" />
              </div>
            </div>
          )}

          <button onClick={onGenerate} disabled={loading}
            className="w-full py-3.5 px-4 bg-green-700 text-white font-semibold rounded-lg hover:bg-green-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-lg">
            {loading ? 'Hämtar erbjudanden...' : 'Nästa: Välj bästa köp →'}
          </button>
        </div>
      </div>

      {/* SEO content */}
      <section className="mt-10 space-y-6 text-sm text-gray-600">
        <div>
          <h2 className="text-base font-semibold text-gray-900 mb-2">Menyplanering som sparar dig pengar</h2>
          <p className="leading-relaxed">Att planera veckans middagar behöver inte vara svårt eller dyrt. Med Veckosmak får du en komplett veckomeny baserad på de bästa erbjudandena från din lokala matbutik.</p>
        </div>
        <div>
          <h2 className="text-base font-semibold text-gray-900 mb-2">Så här fungerar Veckosmak</h2>
          <p className="leading-relaxed">Varje vecka hämtar vi erbjudanden från ICA Maxi och matchar dem mot över 600 recept med crowd-betyg. Resultatet är en skräddarsydd veckomeny med näringsinfo, inköpslista och uppskattad besparing.</p>
        </div>
        <div>
          <h2 className="text-base font-semibold text-gray-900 mb-2">Perfekt för familjer i Örebro</h2>
          <p className="leading-relaxed">Veckosmak började med ICA Maxi Boglundsängen i Örebro och expanderar snart till fler butiker. Spara tid på matplanering och pengar på matkassan.</p>
        </div>
      </section>
    </div>
  )
}
