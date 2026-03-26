import { useState, useEffect } from 'react'

// Map regions/cities so "Stockholm" finds Nacka, Solna, Arninge etc.
const REGION_ALIASES = {
  'stockholm': ['arninge','barkarbystaden','haninge','nacka','solna','lindhagen','bromma','flemingsberg','botkyrka','haggvik','osteraker','varmd','nynashamn','tumba'],
  'göteborg': ['angered','backaplan','goteborg','hogsbo','torslanda','partille','kungalv'],
  'malmö': ['malmo','burlov','toftanas','vastra hamnen','loddekopin'],
  'örebro': ['orebro','boglundsangen','universitetet'],
  'uppsala': ['stenhagen','gnista'],
  'västerås': ['erikslund','halla','vasteras'],
  'halmstad': ['hogskolan','flygstaden'],
  'helsingborg': ['raa','hyllinge'],
  'södertälje': ['vasa handelsplats','moraberg','sodertalje'],
  'gävle': ['gavle','brynas'],
  'karlstad': ['valsviken'],
  'lund': ['gunnesbo'],
}

function normalize(s) {
  return s.toLowerCase()
    .replace(/å/g,'a').replace(/ä/g,'a').replace(/ö/g,'o')
    .replace(/é/g,'e').replace(/ü/g,'u')
}

function matchesSearch(city, query, address = '') {
  if (!query) return true
  const q = normalize(query)
  const c = normalize(city)
  const a = normalize(address)
  // Direct match in city or address
  if (c.includes(q) || a.includes(q)) return true
  // Region alias match
  for (const [region, aliases] of Object.entries(REGION_ALIASES)) {
    if (region.includes(q) || normalize(region).includes(q)) {
      if (aliases.some(al => c.includes(al) || a.includes(al))) return true
    }
  }
  return false
}

function StoreSelector({ preferences, update }) {
  const [stores, setStores] = useState(null)
  const [search, setSearch] = useState('')
  const [open, setOpen] = useState(false)

  useEffect(() => {
    fetch('/api/stores')
      .then(r => r.ok ? r.json() : { stores: {} })
      .then(d => setStores(d.stores || {}))
      .catch(() => {})
  }, [])

  const currentStore = stores?.[preferences.store_id]
  const currentName = currentStore?.city || 'Örebro Boglundsängen'

  const filtered = stores ? Object.entries(stores)
    .filter(([_, s]) => matchesSearch(s.city, search, s.address || ''))
    .sort((a, b) => a[1].city.localeCompare(b[1].city, 'sv'))
    : []

  return (
    <div className="mb-6">
      <button onClick={() => setOpen(!open)}
        className="w-full text-left px-4 py-2.5 rounded-xl border text-sm flex items-center justify-between"
        style={{ borderColor: 'var(--border)', backgroundColor: 'var(--surface)' }}>
        <div>
          <span className="text-sm">
            <span style={{ color: 'var(--text-muted)' }}>Butik: </span>
            <strong>ICA Maxi {currentName}</strong>
          </span>
          {currentStore?.address && (
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{currentStore.address}</p>
          )}
        </div>
        <span style={{ color: 'var(--text-muted)' }}>{open ? '▲' : 'Byt ▼'}</span>
      </button>

      {open && (
        <div className="mt-2 rounded-xl border overflow-hidden animate-expand"
          style={{ borderColor: 'var(--border)', backgroundColor: 'var(--surface)' }}>
          <input type="text" placeholder="Sök stad eller område..." value={search}
            onChange={e => setSearch(e.target.value)} autoFocus
            className="w-full px-4 py-2.5 text-sm border-b focus:outline-none"
            style={{ borderColor: 'var(--border-light)', backgroundColor: 'var(--bg)' }} />
          <div className="max-h-64 overflow-y-auto">
            {!search && (
              <p className="px-4 py-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                96 butiker — sök t.ex. "Stockholm", "Göteborg" eller din stad
              </p>
            )}
            {filtered.slice(0, 30).map(([id, store]) => (
              <button key={id} onClick={() => { update('store_id', id); setOpen(false); setSearch('') }}
                className="w-full text-left px-4 py-2.5 border-b transition-colors hover:bg-gray-50"
                style={{
                  borderColor: 'var(--border-light)',
                  backgroundColor: id === preferences.store_id ? 'var(--green-soft)' : 'transparent',
                }}>
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm" style={{ fontWeight: id === preferences.store_id ? 600 : 400 }}>{store.city}</span>
                    {store.address && <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{store.address}</p>}
                  </div>
                  {id === preferences.store_id && <span style={{ color: 'var(--green)' }}>✓</span>}
                </div>
              </button>
            ))}
            {search && filtered.length === 0 && (
              <p className="px-4 py-3 text-sm" style={{ color: 'var(--text-muted)' }}>
                Ingen ICA Maxi hittades för "{search}"
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

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
const COMMON_DISLIKES = ['räkor','selleri','koriander','svamp','oliver','paprika','chili','ingefära','kokos','anjovis']
const ALL_DAYS = [
  { value: 'monday', label: 'Mån' },{ value: 'tuesday', label: 'Tis' },
  { value: 'wednesday', label: 'Ons' },{ value: 'thursday', label: 'Tor' },
  { value: 'friday', label: 'Fre' },{ value: 'saturday', label: 'Lör' },
  { value: 'sunday', label: 'Sön' },
]

function Pill({ active, onClick, children, variant = 'green' }) {
  const s = variant === 'red' && active
    ? { backgroundColor: '#fef2f2', color: '#b91c1c', borderColor: '#fecaca' }
    : active
      ? { backgroundColor: 'var(--green)', color: 'white', borderColor: 'var(--green)' }
      : { borderColor: 'var(--border)' }
  return <button onClick={onClick} style={s} className="px-3.5 py-2 rounded-full text-sm border transition-all hover:shadow-sm">{children}</button>
}

function Stepper({ value, onChange, min, max, label }) {
  return (
    <div>
      <label className="block text-sm font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>{label}</label>
      <div className="flex items-center gap-3">
        <button onClick={() => onChange(Math.max(min, value - 1))}
          className="w-11 h-11 rounded-full border text-lg font-medium transition-colors hover:shadow-sm" style={{ borderColor: 'var(--border)' }}>−</button>
        <span className="text-xl font-semibold w-12 text-center">{value}</span>
        <button onClick={() => onChange(Math.min(max, value + 1))}
          className="w-11 h-11 rounded-full border text-lg font-medium transition-colors hover:shadow-sm" style={{ borderColor: 'var(--border)' }}>+</button>
      </div>
    </div>
  )
}

// Static demo menu for "value before effort"
function DemoMenu() {
  const meals = [
    { day: 'Måndag', title: 'Kycklingwok med grönsaker', time: 25, price: 32, stars: 4.3 },
    { day: 'Tisdag', title: 'Pasta carbonara', time: 20, price: 18, stars: 4.6 },
    { day: 'Onsdag', title: 'Laxfilé med potatisgratäng', time: 40, price: 38, stars: 4.5 },
    { day: 'Torsdag', title: 'Köttfärssås med spaghetti', time: 30, price: 22, stars: 4.4 },
  ]
  return (
    <div className="rounded-2xl border p-4 mb-8" style={{ backgroundColor: 'var(--surface)', borderColor: 'var(--border)' }}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-sm">Exempel: Så kan din vecka se ut</h3>
        <span className="text-xs font-medium px-2 py-0.5 rounded-full" style={{ backgroundColor: 'var(--green-soft)', color: 'var(--green)' }}>
          Sparar ~280 kr
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {meals.map(m => (
          <div key={m.day} className="p-2.5 rounded-xl" style={{ backgroundColor: 'var(--bg)' }}>
            <p className="text-xs font-medium" style={{ color: 'var(--green)' }}>{m.day}</p>
            <p className="text-sm font-medium mt-0.5 leading-snug">{m.title}</p>
            <div className="flex items-center gap-2 mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
              <span className="text-amber-400">{'★'.repeat(Math.round(m.stars))}</span>
              <span>{m.time} min</span>
              <span style={{ color: 'var(--accent)' }}>{m.price} kr/port</span>
            </div>
          </div>
        ))}
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

  const setTimeMix = (preset) => {
    if (!preset) setPreferences({ ...preferences, max_cook_time: null, time_mix: null })
    else if (preset.q) setPreferences({ ...preferences, max_cook_time: 30, time_mix: null })
    else if (preset.mix) {
      const q = Math.ceil(preferences.num_dinners / 2)
      setPreferences({ ...preferences, max_cook_time: null, time_mix: { quick_count: q, medium_count: 0, slow_count: preferences.num_dinners - q } })
    } else if (preset.max) setPreferences({ ...preferences, max_cook_time: preset.max, time_mix: null })
  }
  const tmMode = preferences.time_mix ? 'mix' : preferences.max_cook_time ? 'max' : 'none'

  return (
    <div className="animate-fade-in">
      {/* Hero */}
      <section className="text-center mb-8">
        <h1 className="text-3xl font-bold tracking-tight mb-3">
          Middagar som sparar dig <span style={{ color: 'var(--accent)' }}>pengar</span>
        </h1>
        <p className="text-base leading-relaxed max-w-md mx-auto" style={{ color: 'var(--text-secondary)' }}>
          Vi matchar veckans erbjudanden mot populära recept och skapar
          en komplett veckomeny med inköpslista.
        </p>
        <div className="flex items-center justify-center gap-6 mt-4 text-sm" style={{ color: 'var(--text-muted)' }}>
          <span>600+ recept</span>
          <span style={{ color: 'var(--border)' }}>·</span>
          <span>Spara 200–400 kr/v</span>
          <span style={{ color: 'var(--border)' }}>·</span>
          <span>Helt gratis</span>
        </div>
      </section>

      {/* Demo menu — value before effort */}
      {!isReturning && <DemoMenu />}

      {/* Returning user — single clear CTA */}
      {isReturning && (
        <div className="mb-6 animate-fade-in">
          <button onClick={onGenerateDirect} disabled={loading}
            className="w-full py-4 rounded-xl text-white font-semibold text-lg disabled:opacity-50 transition-colors"
            style={{ backgroundColor: 'var(--accent)' }}>
            Skapa veckans meny
          </button>
          <button onClick={() => setShowMore(true)}
            className="w-full text-sm mt-2 py-1" style={{ color: 'var(--text-muted)' }}>
            Ändra inställningar först
          </button>
        </div>
      )}

      {/* Store picker */}
      <StoreSelector preferences={preferences} update={update} />

      {/* Form — hidden for returning users unless they click "Ändra" */}
      {(!isReturning || showMore) && (
        <div className="rounded-2xl p-6 border animate-fade-in" style={{ backgroundColor: 'var(--surface)', borderColor: 'var(--border)' }}>
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-6">
              <Stepper value={preferences.household_size} onChange={v => update('household_size', v)} min={1} max={8} label="Antal personer" />
              {!useSpecificDays && <Stepper value={preferences.num_dinners} onChange={v => update('num_dinners', v)} min={1} max={7} label="Middagar" />}
            </div>

            {/* Advanced toggle */}
            <button onClick={() => setShowMore(!showMore)}
              className="w-full text-sm py-1" style={{ color: 'var(--text-muted)' }}>
              {showMore && hasAdvanced ? 'Dölj ▲' : `Fler inställningar${hasAdvanced ? ' (aktiva)' : ''} ▼`}
            </button>

            {showMore && (
              <div className="space-y-5 pt-4 animate-expand" style={{ borderTop: '1px solid var(--border-light)' }}>
                <label className="flex items-center gap-3 cursor-pointer text-sm">
                  <input type="checkbox" checked={preferences.has_children} onChange={e => update('has_children', e.target.checked)}
                    className="w-5 h-5 rounded accent-green-700" />
                  Hushållet har barn
                </label>

                {/* Days */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>Specifika dagar</label>
                    <input type="checkbox" checked={useSpecificDays}
                      onChange={e => {
                        if (!e.target.checked) setPreferences({ ...preferences, selected_days: [] })
                        else setPreferences({ ...preferences, selected_days: ALL_DAYS.slice(0, preferences.num_dinners).map(d => d.value) })
                      }} className="w-5 h-5 rounded accent-green-700" />
                  </div>
                  {useSpecificDays && (
                    <div className="flex gap-1.5">
                      {ALL_DAYS.map(d => (
                        <button key={d.value} onClick={() => toggleDay(d.value)}
                          className="w-11 h-11 rounded-full text-xs font-medium border transition-all"
                          style={(preferences.selected_days||[]).includes(d.value)?{backgroundColor:'var(--green)',color:'white',borderColor:'var(--green)'}:{borderColor:'var(--border)'}}>
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
                      className="w-full h-1.5 rounded-lg appearance-none cursor-pointer accent-green-700" style={{ backgroundColor: 'var(--border)' }} />
                  )}
                </div>

                {/* Time */}
                <div>
                  <label className="block text-sm font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>Tillagningstid</label>
                  <div className="flex gap-2 flex-wrap">
                    {[['Alla',null],['≤30 min',{q:1}],['Blandning',{mix:1}],['≤45 min',{max:45}]].map(([l,v],i) => {
                      const active = (!v&&tmMode==='none')||(v?.q&&preferences.max_cook_time===30&&!preferences.time_mix)||(v?.mix&&!!preferences.time_mix)||(v?.max&&preferences.max_cook_time===v.max)
                      return <Pill key={i} active={active} onClick={() => setTimeMix(v)}>{l}</Pill>
                    })}
                  </div>
                </div>

                {/* Diet */}
                <div>
                  <label className="block text-sm font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>Kostval</label>
                  <div className="flex gap-2 flex-wrap">
                    {DIET_OPTIONS.map(o => <Pill key={o.value} active={preferences.dietary_restrictions.includes(o.value)} onClick={() => toggleList('dietary_restrictions',o.value)}>{o.label}</Pill>)}
                  </div>
                </div>

                {/* Lifestyle */}
                <div>
                  <label className="block text-sm font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>Livsstil</label>
                  <div className="flex gap-2 flex-wrap">
                    {LIFESTYLE_OPTIONS.map(o => <Pill key={o.value} active={(preferences.lifestyle_preferences||[]).includes(o.value)} onClick={() => toggleList('lifestyle_preferences',o.value)}>{o.label}</Pill>)}
                  </div>
                </div>

                {/* Disliked */}
                <div>
                  <label className="block text-sm font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>Undvik</label>
                  <div className="flex gap-1.5 flex-wrap mb-2">
                    {COMMON_DISLIKES.map(i => <Pill key={i} active={preferences.disliked_ingredients.includes(i)} onClick={() => toggleList('disliked_ingredients',i)} variant="red">{i}</Pill>)}
                  </div>
                  <input type="text" placeholder="Övriga, kommaseparerat"
                    value={preferences.disliked_ingredients.filter(d => !COMMON_DISLIKES.includes(d)).join(', ')}
                    onChange={e => {
                      const custom = e.target.value ? e.target.value.split(',').map(s => s.trim()).filter(Boolean) : []
                      update('disliked_ingredients', [...preferences.disliked_ingredients.filter(d => COMMON_DISLIKES.includes(d)), ...custom])
                    }}
                    className="w-full px-3.5 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-700"
                    style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg)' }} />
                </div>

                {/* Allergy disclaimer */}
                {preferences.dietary_restrictions.length > 0 && (
                  <p className="text-xs p-3 rounded-lg" style={{ backgroundColor: '#fffbeb', color: '#92400e' }}>
                    Dubbelkolla alltid ingredienserna vid allergier eller särskild kost.
                    Recepten filtreras automatiskt men fel kan förekomma.
                  </p>
                )}
              </div>
            )}

            {/* CTA */}
            <button onClick={onGenerate} disabled={loading}
              className="w-full py-3.5 rounded-xl text-white font-semibold text-base disabled:opacity-50 transition-colors"
              style={{ backgroundColor: 'var(--accent)' }}>
              {loading ? 'Hämtar erbjudanden...' : 'Skapa min veckomeny'}
            </button>
          </div>
        </div>
      )}

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
