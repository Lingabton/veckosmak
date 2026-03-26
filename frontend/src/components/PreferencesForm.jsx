import { useState, useEffect } from 'react'

const DIETS = [
  { v: 'vegetarian', l: 'Vegetarisk' }, { v: 'vegan', l: 'Vegansk' },
  { v: 'glutenfree', l: 'Glutenfri' }, { v: 'dairyfree', l: 'Mjölkfri' },
  { v: 'lactosefree', l: 'Laktosfri' }, { v: 'porkfree', l: 'Fläskfri' },
]
const LIFESTYLES = [
  { v: 'avoid_processed', l: 'Undvik processad' }, { v: 'prefer_healthy', l: 'Hälsosammare' },
  { v: 'prefer_highprotein', l: 'Proteinrikt' }, { v: 'prefer_lowcarb', l: 'Lågkolhydrat' },
  { v: 'prefer_sustainable', l: 'Klimatsmart' }, { v: 'reduce_waste', l: 'Minska svinn' },
]
const DISLIKES = ['räkor','selleri','koriander','svamp','oliver','paprika','chili','ingefära','kokos','anjovis']
const DAYS = [{v:'monday',l:'Mån'},{v:'tuesday',l:'Tis'},{v:'wednesday',l:'Ons'},{v:'thursday',l:'Tor'},{v:'friday',l:'Fre'},{v:'saturday',l:'Lör'},{v:'sunday',l:'Sön'}]

// Store selector
function StoreSelector({ preferences, update }) {
  const [stores, setStores] = useState(null)
  const [search, setSearch] = useState('')
  const [open, setOpen] = useState(false)
  useEffect(() => {
    fetch('/api/stores', { signal: AbortSignal.timeout(45000) })
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d?.stores) setStores(d.stores) })
      .catch(() => {})
  }, [])

  const cur = stores?.[preferences.store_id]
  const type = {maxi:'Maxi',kvantum:'Kvantum',supermarket:'Supermarket',nara:'Nära'}[cur?.type] || 'Maxi'

  const normalize = s => s.toLowerCase().replace(/[åÅ]/g,'a').replace(/[äÄ]/g,'a').replace(/[öÖ]/g,'o').replace(/[éÉ]/g,'e')
  const ALIASES = {
    'stockholm':['arninge','barkarbystaden','haninge','nacka','solna','lindhagen','bromma','flemingsberg','botkyrka','haggvik','osteraker','varmd','nynashamn'],
    'göteborg':['angered','backaplan','goteborg','hogsbo','torslanda','partille','kungalv'],
    'malmö':['malmo','burlov','toftanas','vastra hamnen'],
    'örebro':['orebro','boglundsangen','universitetet'],
    'uppsala':['stenhagen','gnista'],'västerås':['erikslund','halla','vasteras'],
    'södertälje':['vasa handelsplats','moraberg','sodertalje'],'gävle':['gavle','brynas'],
  }
  const match = (city, addr, q) => {
    if (!q) return true
    const nq = normalize(q), nc = normalize(city), na = normalize(addr||'')
    if (nc.includes(nq) || na.includes(nq)) return true
    for (const [r, aliases] of Object.entries(ALIASES))
      if (r.includes(nq) || normalize(r).includes(nq))
        if (aliases.some(a => nc.includes(a) || na.includes(a))) return true
    return false
  }

  const filtered = stores ? Object.entries(stores)
    .filter(([_,s]) => match(s.city, s.address, search))
    .sort((a,b) => { if (search && a[1].rank !== b[1].rank) return a[1].rank - b[1].rank; return a[1].city.localeCompare(b[1].city,'sv') })
    : []

  const typeColor = {maxi:'var(--color-accent)',kvantum:'var(--color-brand)',supermarket:'var(--color-text-secondary)',nara:'var(--color-text-muted)'}

  return (
    <div className="mb-6">
      <button onClick={() => setOpen(!open)} className="card w-full text-left px-4 py-3 flex items-center justify-between">
        <div>
          <p className="text-sm font-medium">ICA {type} {cur?.city || 'Örebro Boglundsängen'}</p>
          {cur?.address && <p className="text-xs mt-0.5" style={{color:'var(--color-text-muted)'}}>{cur.address}</p>}
        </div>
        <span className="text-sm" style={{color:'var(--color-text-muted)'}}>{open ? '▲' : 'Byt butik'}</span>
      </button>
      {open && (
        <div className="card mt-2 overflow-hidden expand">
          <input type="text" placeholder="Sök stad..." value={search} onChange={e=>setSearch(e.target.value)} autoFocus
            className="w-full px-4 py-3 text-sm border-b outline-none" style={{borderColor:'var(--color-border-light)',background:'var(--color-bg)'}} />
          <div className="max-h-64 overflow-y-auto">
            {!stores && <p className="px-4 py-3 text-xs" style={{color:'var(--color-text-muted)'}}>Laddar butiker... (kan ta 30 sek vid uppstart)</p>}
            {stores && !search && <p className="px-4 py-2 text-xs" style={{color:'var(--color-text-muted)'}}>1100+ butiker — sök din stad</p>}
            {filtered.slice(0,25).map(([id,s]) => (
              <button key={id} onClick={()=>{update('store_id',id);setOpen(false);setSearch('')}}
                className="w-full text-left px-4 py-2.5 border-b hover:bg-gray-50 transition-colors"
                style={{borderColor:'var(--color-border-light)', background: id===preferences.store_id?'var(--color-brand-light)':'transparent'}}>
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium">{s.city}</span>
                    <span className="text-xs ml-2 font-medium" style={{color:typeColor[s.type]||'var(--color-text-muted)'}}>
                      {({maxi:'Maxi',kvantum:'Kvantum',supermarket:'Super',nara:'Nära'})[s.type]}
                    </span>
                    {s.address && <p className="text-xs" style={{color:'var(--color-text-muted)'}}>{s.address}</p>}
                  </div>
                  {id===preferences.store_id && <span style={{color:'var(--color-brand)'}}>✓</span>}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default function PreferencesForm({ preferences, setPreferences, goToOffers, generateMenu, loading, isReturning }) {
  const [showMore, setShowMore] = useState(false)
  const update = (k,v) => setPreferences({...preferences, [k]: v})
  const toggle = (k,v) => { const c = preferences[k]||[]; update(k, c.includes(v)?c.filter(d=>d!==v):[...c,v]) }
  const hasAdv = preferences.dietary_restrictions?.length>0||(preferences.lifestyle_preferences||[]).length>0||preferences.disliked_ingredients?.length>0||preferences.has_children||preferences.budget_per_week!==null

  return (
    <div className="fade-up">
      {/* Hero */}
      <section className="text-center mb-10">
        <h1 className="text-4xl font-bold tracking-tight leading-tight mb-4">
          Middagar som sparar<br/>dig <span style={{color:'var(--color-accent)'}}>pengar</span>
        </h1>
        <p className="text-lg leading-relaxed max-w-md mx-auto" style={{color:'var(--color-text-secondary)'}}>
          Vi matchar veckans erbjudanden mot populära recept och skapar din veckomeny med inköpslista.
        </p>
        <div className="flex items-center justify-center gap-6 mt-6 text-sm font-medium" style={{color:'var(--color-text-muted)'}}>
          <span>600+ recept</span>
          <span className="w-1 h-1 rounded-full" style={{background:'var(--color-border)'}} />
          <span>Spara 200–400 kr/v</span>
          <span className="w-1 h-1 rounded-full" style={{background:'var(--color-border)'}} />
          <span>Helt gratis</span>
        </div>
      </section>

      {/* Demo preview for new users */}
      {!isReturning && (
        <div className="card p-5 mb-8 fade-in">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold">Exempel: Så kan din vecka se ut</h3>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full" style={{background:'var(--color-brand-light)',color:'var(--color-brand)'}}>Sparar ~280 kr</span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {[
              {d:'Mån',t:'Kycklingwok med grönsaker',m:25,p:32,s:4.3},
              {d:'Tis',t:'Pasta carbonara',m:20,p:18,s:4.6},
              {d:'Ons',t:'Laxfilé med potatisgratäng',m:40,p:38,s:4.5},
              {d:'Tor',t:'Köttfärssås med spaghetti',m:30,p:22,s:4.4},
            ].map(r => (
              <div key={r.d} className="p-3 rounded-xl" style={{background:'var(--color-bg)'}}>
                <p className="text-xs font-semibold" style={{color:'var(--color-brand)'}}>{r.d}</p>
                <p className="text-sm font-medium mt-0.5 leading-snug">{r.t}</p>
                <p className="text-xs mt-1" style={{color:'var(--color-text-muted)'}}>
                  <span className="text-amber-400">{'★'.repeat(Math.round(r.s))}</span> {r.m} min · <span style={{color:'var(--color-accent)'}}>{r.p} kr/p</span>
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Returning user shortcut */}
      {isReturning && (
        <div className="mb-6 fade-in">
          <button onClick={generateMenu} disabled={loading} className="btn btn-primary w-full text-lg py-4">
            Skapa veckans meny
          </button>
          <button onClick={() => setShowMore(true)} className="w-full text-sm mt-2 py-1" style={{color:'var(--color-text-muted)'}}>
            Ändra inställningar
          </button>
        </div>
      )}

      <StoreSelector preferences={preferences} update={update} />

      {/* Form */}
      {(!isReturning || showMore) && (
        <div className="card p-6 fade-in">
          <div className="space-y-6">
            {/* Core settings */}
            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium mb-2" style={{color:'var(--color-text-secondary)'}}>Antal personer</label>
                <div className="flex items-center gap-3">
                  <button className="stepper-btn" onClick={()=>update('household_size',Math.max(1,preferences.household_size-1))}>−</button>
                  <span className="text-2xl font-bold w-8 text-center">{preferences.household_size}</span>
                  <button className="stepper-btn" onClick={()=>update('household_size',Math.min(8,preferences.household_size+1))}>+</button>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2" style={{color:'var(--color-text-secondary)'}}>Middagar</label>
                <div className="flex items-center gap-3">
                  <button className="stepper-btn" onClick={()=>update('num_dinners',Math.max(1,preferences.num_dinners-1))}>−</button>
                  <span className="text-2xl font-bold w-8 text-center">{preferences.num_dinners}</span>
                  <button className="stepper-btn" onClick={()=>update('num_dinners',Math.min(7,preferences.num_dinners+1))}>+</button>
                </div>
              </div>
            </div>

            {/* More settings toggle */}
            <button onClick={()=>setShowMore(!showMore)}
              className="w-full text-sm py-2 font-medium transition-colors" style={{color:'var(--color-text-muted)'}}>
              {showMore ? 'Dölj inställningar ▲' : `Fler inställningar${hasAdv?' ●':''} ▼`}
            </button>

            {showMore && (
              <div className="space-y-5 pt-4 expand" style={{borderTop:'1px solid var(--color-border-light)'}}>
                <label className="flex items-center gap-3 cursor-pointer">
                  <input type="checkbox" checked={preferences.has_children} onChange={e=>update('has_children',e.target.checked)}
                    className="w-5 h-5 rounded accent-green-700" />
                  <span className="text-sm">Hushållet har barn</span>
                </label>

                {/* Budget */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium" style={{color:'var(--color-text-secondary)'}}>Budget</span>
                    <label className="flex items-center gap-2 text-xs cursor-pointer" style={{color:'var(--color-text-muted)'}}>
                      {preferences.budget_per_week ? `${preferences.budget_per_week} kr` : 'Av'}
                      <input type="checkbox" checked={preferences.budget_per_week!==null} onChange={e=>update('budget_per_week',e.target.checked?1000:null)}
                        className="w-4 h-4 rounded accent-green-700" />
                    </label>
                  </div>
                  {preferences.budget_per_week!==null && (
                    <input type="range" min="300" max="2000" step="100" value={preferences.budget_per_week}
                      onChange={e=>update('budget_per_week',Number(e.target.value))}
                      className="w-full h-1.5 rounded-lg appearance-none cursor-pointer accent-green-700"
                      style={{background:'var(--color-border)'}} />
                  )}
                </div>

                {/* Diet */}
                <div>
                  <p className="text-sm font-medium mb-2" style={{color:'var(--color-text-secondary)'}}>Kostval</p>
                  <div className="flex gap-2 flex-wrap">
                    {DIETS.map(d => (
                      <button key={d.v} onClick={()=>toggle('dietary_restrictions',d.v)}
                        className={`btn-pill ${preferences.dietary_restrictions.includes(d.v)?'active':''}`}>{d.l}</button>
                    ))}
                  </div>
                </div>

                {/* Lifestyle */}
                <div>
                  <p className="text-sm font-medium mb-2" style={{color:'var(--color-text-secondary)'}}>Livsstil</p>
                  <div className="flex gap-2 flex-wrap">
                    {LIFESTYLES.map(d => (
                      <button key={d.v} onClick={()=>toggle('lifestyle_preferences',d.v)}
                        className={`btn-pill ${(preferences.lifestyle_preferences||[]).includes(d.v)?'active':''}`}>{d.l}</button>
                    ))}
                  </div>
                </div>

                {/* Disliked */}
                <div>
                  <p className="text-sm font-medium mb-2" style={{color:'var(--color-text-secondary)'}}>Undvik</p>
                  <div className="flex gap-1.5 flex-wrap">
                    {DISLIKES.map(d => (
                      <button key={d} onClick={()=>toggle('disliked_ingredients',d)}
                        className={`btn-pill text-xs ${preferences.disliked_ingredients.includes(d)?'active-red':''}`}>{d}</button>
                    ))}
                  </div>
                </div>

                {preferences.dietary_restrictions.length > 0 && (
                  <p className="text-xs p-3 rounded-xl" style={{background:'#fffbeb',color:'#92400e'}}>
                    Dubbelkolla alltid ingredienserna vid allergier. Recepten filtreras automatiskt men fel kan förekomma.
                  </p>
                )}
              </div>
            )}

            <button onClick={goToOffers} disabled={loading} className="btn btn-primary w-full">
              {loading ? 'Hämtar erbjudanden...' : 'Skapa min veckomeny'}
            </button>
          </div>
        </div>
      )}

      {/* SEO */}
      <section className="mt-14 space-y-6 text-sm" style={{color:'var(--color-text-muted)'}}>
        <div>
          <h2 className="text-base font-bold mb-1" style={{color:'var(--color-text)'}}>Menyplanering som sparar pengar</h2>
          <p>Med Veckosmak får du en veckomeny baserad på erbjudanden från din lokala matbutik. Vår AI matchar recept mot kampanjer.</p>
        </div>
        <div>
          <h2 className="text-base font-bold mb-1" style={{color:'var(--color-text)'}}>Så fungerar det</h2>
          <p>Varje vecka hämtar vi erbjudanden från 1100+ ICA-butiker och matchar dem mot 600+ recept med betyg och näringsinfo.</p>
        </div>
      </section>
    </div>
  )
}
