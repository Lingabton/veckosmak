import { useState, useEffect } from 'react'
import EmailSignup from './EmailSignup'

const DIETS = [
  {v:'vegetarian',l:'Vegetarisk'},{v:'vegan',l:'Vegansk'},{v:'glutenfree',l:'Glutenfri'},
  {v:'dairyfree',l:'Mjölkfri'},{v:'lactosefree',l:'Laktosfri'},{v:'porkfree',l:'Fläskfri'},
]
const LIFESTYLES = [
  {v:'avoid_processed',l:'Undvik processad'},{v:'prefer_healthy',l:'Hälsosammare'},
  {v:'prefer_highprotein',l:'Proteinrikt'},{v:'prefer_lowcarb',l:'Lågkolhydrat'},
  {v:'prefer_sustainable',l:'Klimatsmart'},{v:'reduce_waste',l:'Minska svinn'},
]
const DISLIKES = ['räkor','selleri','koriander','svamp','oliver','paprika','chili','ingefära','kokos','anjovis']

function StoreSelector({ preferences, update }) {
  const [stores, setStores] = useState(null)
  const [search, setSearch] = useState('')
  const [open, setOpen] = useState(false)
  useEffect(() => {
    fetch('/api/stores', {signal: AbortSignal.timeout(45000)})
      .then(r => r.ok ? r.json() : null).then(d => { if (d?.stores) setStores(d.stores) }).catch(() => {})
  }, [])
  const cur = stores?.[preferences.store_id]
  const type = {maxi:'Maxi',kvantum:'Kvantum',supermarket:'Supermarket',nara:'Nära'}[cur?.type] || 'Maxi'
  const normalize = s => s.toLowerCase().replace(/[åÅ]/g,'a').replace(/[äÄ]/g,'a').replace(/[öÖ]/g,'o').replace(/[éÉ]/g,'e')
  const ALIASES = {'stockholm':['arninge','barkarbystaden','haninge','nacka','solna','lindhagen','bromma','flemingsberg','botkyrka','haggvik','osteraker','varmd','nynashamn'],
    'göteborg':['angered','backaplan','goteborg','hogsbo','torslanda','partille','kungalv'],'malmö':['malmo','burlov','toftanas','vastra hamnen'],
    'örebro':['orebro','boglundsangen','universitetet'],'uppsala':['stenhagen','gnista'],'västerås':['erikslund','halla','vasteras'],
    'södertälje':['vasa handelsplats','moraberg','sodertalje'],'gävle':['gavle','brynas']}
  const match = (city, addr, q) => {
    if (!q) return true
    const nq=normalize(q), nc=normalize(city), na=normalize(addr||'')
    if (nc.includes(nq)||na.includes(nq)) return true
    for (const [r,als] of Object.entries(ALIASES)) if (r.includes(nq)||normalize(r).includes(nq)) if (als.some(a=>nc.includes(a)||na.includes(a))) return true
    return false
  }
  const filtered = stores ? Object.entries(stores).filter(([_,s])=>match(s.city,s.address,search))
    .sort((a,b)=>{if(search&&a[1].rank!==b[1].rank)return a[1].rank-b[1].rank;return a[1].city.localeCompare(b[1].city,'sv')}) : []
  const typeColor={maxi:'var(--color-accent)',kvantum:'var(--color-brand)',supermarket:'var(--color-text-secondary)',nara:'var(--color-text-muted)'}
  const typeLabel={maxi:'Maxi',kvantum:'Kvantum',supermarket:'Super',nara:'Nära'}

  return (
    <div className="mb-5">
      <button onClick={()=>setOpen(!open)} className="card w-full text-left px-5 py-4 flex items-center justify-between" style={{
        borderLeft: '4px solid var(--color-brand)',
      }}>
        <div>
          <p className="text-[11px] uppercase tracking-widest font-medium mb-1" style={{color:'var(--color-text-muted)'}}>Din butik</p>
          <p className="text-base font-bold">{cur?.name || 'Välj din butik'}</p>
          <p className="text-xs mt-0.5" style={{color:'var(--color-text-muted)'}}>
            {cur ? `${cur.city} · Menyn byggs från denna butiks erbjudanden` : 'Vi hämtar erbjudanden från butiken du väljer'}
          </p>
        </div>
        <span className="text-sm font-medium" style={{color:'var(--color-brand)'}}>{open ? '▲' : 'Byt butik'}</span>
      </button>
      {open && (
        <div className="card mt-2 overflow-hidden expand">
          <input type="text" placeholder="Sök stad..." value={search} onChange={e=>setSearch(e.target.value)} autoFocus
            className="w-full px-4 py-3 text-sm border-b outline-none" style={{borderColor:'var(--color-border-light)',background:'var(--color-bg)'}} />
          <div className="max-h-[60vh] overflow-y-auto">
            {!stores && <p className="px-4 py-3 text-xs" style={{color:'var(--color-text-muted)'}}>Laddar butiker...</p>}
            {stores && !search && <p className="px-4 py-2 text-xs" style={{color:'var(--color-text-muted)'}}>1 300+ butiker — sök din stad</p>}
            {filtered.slice(0,25).map(([id,s])=>(
              <button key={id} onClick={()=>{update('store_id',id);setOpen(false);setSearch('')}}
                className="w-full text-left px-4 py-2.5 border-b hover:bg-gray-50 transition-colors"
                style={{borderColor:'var(--color-border-light)',background:id===preferences.store_id?'var(--color-brand-light)':'transparent'}}>
                <span className="text-sm font-medium">{s.city}</span>
                <span className="text-xs ml-2 font-medium" style={{color:typeColor[s.type]||'var(--color-text-muted)'}}>{typeLabel[s.type]}</span>
                {s.address && <p className="text-xs" style={{color:'var(--color-text-muted)'}}>{s.address}</p>}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// Product mockup — shows what you get
function ProductPreview() {
  return (
    <div className="card p-5 mb-8">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Menu preview */}
        <div>
          <p className="text-xs font-bold uppercase tracking-wider mb-2" style={{color:'var(--color-brand)'}}>Din veckomeny</p>
          {[{d:'Mån',t:'Kycklingwok',p:'32 kr/p'},{d:'Tis',t:'Pasta carbonara',p:'18 kr/p'},{d:'Ons',t:'Laxgratäng',p:'35 kr/p'},{d:'Tor',t:'Köttfärssås',p:'22 kr/p'}].map(r=>(
            <div key={r.d} className="flex items-center justify-between py-1.5 text-sm" style={{borderBottom:'1px solid var(--color-border-light)'}}>
              <div><span className="font-medium" style={{color:'var(--color-text-secondary)'}}>{r.d}</span> <span>{r.t}</span></div>
              <span style={{color:'var(--color-accent)'}}>{r.p}</span>
            </div>
          ))}
          <div className="flex items-center justify-between mt-2 pt-2" style={{borderTop:'1px solid var(--color-border)'}}>
            <span className="text-sm font-bold">Veckokostnad</span>
            <div className="text-right">
              <span className="font-bold" style={{color:'var(--color-accent)'}}>~580 kr</span>
              <span className="text-xs ml-1.5" style={{color:'var(--color-brand)'}}>sparar ~240 kr</span>
            </div>
          </div>
        </div>
        {/* Shopping list preview */}
        <div>
          <p className="text-xs font-bold uppercase tracking-wider mb-2" style={{color:'var(--color-brand)'}}>Inköpslista</p>
          {['Kycklingfilé 89 kr/kg','Pasta','Laxfilé 2 för 89 kr','Nötfärs','Grädde','Broccoli','Potatis','Ost'].map((item,i)=>(
            <div key={i} className="flex items-center gap-2 py-1 text-xs" style={{borderBottom:'1px solid var(--color-border-light)'}}>
              <div className="w-3.5 h-3.5 rounded-full border" style={{borderColor:'var(--color-border)'}} />
              <span>{item}</span>
            </div>
          ))}
          <p className="text-xs mt-2 font-medium" style={{color:'var(--color-brand)'}}>12 varor · 4 på erbjudande</p>
        </div>
      </div>
    </div>
  )
}

export default function PreferencesForm({ preferences, setPreferences, goToOffers, generateMenu, loading, isReturning, menu, setView, totalSavings, menuHistory }) {
  const [showMore, setShowMore] = useState(false)
  const update = (k,v) => setPreferences({...preferences,[k]:v})
  const toggle = (k,v) => {const c=preferences[k]||[];update(k,c.includes(v)?c.filter(d=>d!==v):[...c,v])}
  const hasAdv = preferences.dietary_restrictions?.length>0||(preferences.lifestyle_preferences||[]).length>0||preferences.disliked_ingredients?.length>0||preferences.has_children||preferences.budget_per_week!==null

  return (
    <div className="fade-up">

      {/* === SECTION 1: Hero === */}
      <section className="-mx-5 -mt-8 px-5 pt-16 pb-12 mb-12 rounded-b-3xl" style={{
        background: 'radial-gradient(ellipse at 50% 20%, #2d8a56 0%, #1a5c35 60%, var(--color-brand-dark) 100%)',
      }}>
        <h1 className="font-display text-4xl sm:text-5xl font-bold leading-[1.1] mb-5 text-white" style={{ letterSpacing: '-0.03em' }}>
          Från erbjudande till{' '}
          <span className="font-display italic" style={{
            background: 'linear-gradient(135deg, var(--color-accent), var(--color-gold))',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>riktig middag</span>
        </h1>
        <p className="text-lg leading-relaxed max-w-md" style={{color:'rgba(255,255,255,0.7)'}}>
          Bygg veckans meny från butikens riktiga kampanjer. Recept, inköpslista och besparing — klar direkt.
        </p>
        <div className="flex flex-wrap items-center gap-3 mt-8">
          {['Butiksspecifika erbjudanden','Färdig inköpslista','1300+ recept'].map(pill => (
            <span key={pill} className="text-sm px-4 py-2 rounded-full text-white" style={{
              background: 'rgba(255,255,255,0.1)',
              backdropFilter: 'blur(8px)',
              WebkitBackdropFilter: 'blur(8px)',
              border: '1px solid rgba(255,255,255,0.15)',
            }}>{pill}</span>
          ))}
        </div>
        <button onClick={generateMenu} className="btn btn-primary mt-8 text-lg px-8 py-4">
          Skapa min veckomeny
        </button>
        <p className="text-xs mt-3" style={{color:'rgba(255,255,255,0.45)'}}>
          Tar cirka 30 sekunder · Gratis · Ingen inloggning krävs
        </p>
      </section>

      {/* Saved menu + savings tracker */}
      {menu && (
        <div className="rounded-2xl p-6 mb-6 fade-in" style={{
          background: 'var(--color-brand-dark)',
          color: 'white',
        }}>
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="font-bold text-white">Din veckomeny</p>
              <p className="text-sm" style={{color:'rgba(255,255,255,0.6)'}}>
                {menu.store_name||'ICA'} · {menu.meals?.length} middagar · ~{Math.round(menu.total_cost)} kr
              </p>
            </div>
            {totalSavings > 0 && (
              <div className="text-right">
                <p className="text-xs" style={{color:'rgba(255,255,255,0.5)'}}>Totalt sparat jmf. ord. pris</p>
                <p className="font-display text-3xl font-bold" style={{color:'var(--color-gold)'}}>Du sparar {Math.round(totalSavings)} kr</p>
              </div>
            )}
          </div>
          <div className="flex gap-2">
            <button onClick={()=>setView('shopping')} className="flex-1 py-3 rounded-xl text-sm font-semibold transition-colors" style={{
              background: 'rgba(255,255,255,0.15)',
              backdropFilter: 'blur(8px)',
              WebkitBackdropFilter: 'blur(8px)',
              color: 'white',
              border: '1px solid rgba(255,255,255,0.2)',
            }}>Inköpslista</button>
            <button onClick={()=>setView('menu')} className="flex-1 py-3 rounded-xl text-sm font-semibold transition-colors" style={{
              background: 'transparent',
              color: 'white',
              border: '1px solid rgba(255,255,255,0.3)',
            }}>Visa meny</button>
          </div>
        </div>
      )}

      {/* Product mockup */}
      {!menu && <ProductPreview />}

      {/* === SECTION 2: Så funkar det === */}
      <section className="mb-10">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 sm:gap-4 relative">
          {/* Connecting line on desktop */}
          <div className="hidden sm:block absolute top-6 left-[16.67%] right-[16.67%] h-px" style={{background:'var(--color-border)'}} />
          {[
            {n:'1',t:'Vi läser erbjudanden',d:'Från din valda butik — ICA eller Willys',color:'var(--color-brand)'},
            {n:'2',t:'Vi bygger middagar',d:'Anpassat till ditt hushåll och kostpreferenser',color:'var(--color-accent)'},
            {n:'3',t:'Du får veckan klar',d:'Meny, recept och inköpslista direkt',color:'var(--color-gold)'},
          ].map((s, i) => (
            <div key={s.n} className={`text-center sm:text-center slide-in delay-${i+1} relative`}>
              <p className="font-display text-4xl font-bold mb-2" style={{color:s.color}}>{s.n}</p>
              <p className="text-sm font-semibold">{s.t}</p>
              <p className="text-xs mt-1" style={{color:'var(--color-text-muted)'}}>{s.d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* === Store selector === */}
      <StoreSelector preferences={preferences} update={update} />

      {/* === Core settings — ALWAYS visible === */}
      <div className="card p-6 mb-5">
        <div className="grid grid-cols-2 gap-6 mb-4">
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

        <button onClick={generateMenu} disabled={loading} className="btn btn-primary w-full text-lg py-4">
          {loading ? 'Skapar meny...' : 'Skapa min veckomeny'}
        </button>
        <p className="text-xs text-center mt-2" style={{color:'var(--color-text-muted)'}}>
          Tar cirka 30 sekunder · Gratis · Ingen inloggning krävs
        </p>

        {/* Expand/collapse for advanced settings */}
        <button onClick={()=>setShowMore(!showMore)}
          className="w-full mt-4 py-3 px-4 rounded-xl text-sm font-medium flex items-center justify-between transition-all"
          style={{
            background: showMore ? 'var(--color-brand-light)' : 'var(--color-bg)',
            color: showMore ? 'var(--color-brand-dark)' : 'var(--color-text-secondary)',
            border: `1px solid ${showMore ? 'var(--color-brand)' : 'var(--color-border)'}`,
          }}>
          <span className="flex items-center gap-2">
            <span>{showMore ? 'Dölj filter' : 'Kostfilter, budget och mer'}</span>
            {!showMore && hasAdv && (
              <span className="w-2 h-2 rounded-full" style={{background:'var(--color-accent)'}} />
            )}
          </span>
          <span style={{fontSize:12, opacity:0.6}}>{showMore ? '▲' : '▼'}</span>
        </button>

        {/* Active filters summary when collapsed */}
        {!showMore && hasAdv && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {(preferences.dietary_restrictions||[]).map(d => {
              const label = {vegetarian:'Vegetarisk',vegan:'Vegansk',glutenfree:'Glutenfri',dairyfree:'Mjölkfri',lactosefree:'Laktosfri',porkfree:'Fläskfri'}[d] || d
              return <span key={d} className="text-xs px-2 py-0.5 rounded-full" style={{background:'var(--color-brand-light)',color:'var(--color-brand-dark)'}}>{label}</span>
            })}
            {preferences.budget_per_week && (
              <span className="text-xs px-2 py-0.5 rounded-full" style={{background:'var(--color-border-light)',color:'var(--color-text-secondary)'}}>Budget: {preferences.budget_per_week} kr</span>
            )}
            {preferences.has_children && (
              <span className="text-xs px-2 py-0.5 rounded-full" style={{background:'#fef3c7',color:'#92400e'}}>Barn i hushållet</span>
            )}
          </div>
        )}
      </div>

      {/* === Advanced form — expandable === */}
      {showMore && (
        <div className="card p-6 mb-8">
          <div className="space-y-6">

            {showMore && (
              <div className="space-y-5 expand">
                <label className="flex items-center gap-3 cursor-pointer text-sm">
                  <input type="checkbox" checked={preferences.has_children} onChange={e=>update('has_children',e.target.checked)} className="w-5 h-5 rounded accent-green-700" />
                  Hushållet har barn
                </label>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium" style={{color:'var(--color-text-secondary)'}}>Veckobudget</span>
                    <label className="flex items-center gap-2 text-xs cursor-pointer" style={{color:'var(--color-text-muted)'}}>
                      {preferences.budget_per_week?`${preferences.budget_per_week} kr`:'Av'}
                      <input type="checkbox" checked={preferences.budget_per_week!==null} onChange={e=>update('budget_per_week',e.target.checked?1000:null)} className="w-4 h-4 rounded accent-green-700"/>
                    </label>
                  </div>
                  {preferences.budget_per_week!==null && <input type="range" min="300" max="2000" step="100" value={preferences.budget_per_week} onChange={e=>update('budget_per_week',Number(e.target.value))} className="w-full h-1.5 rounded-lg appearance-none cursor-pointer accent-green-700" style={{background:'var(--color-border)'}}/>}
                </div>
                <div>
                  <p className="text-sm font-medium mb-2" style={{color:'var(--color-text-secondary)'}}>Kostval</p>
                  <div className="flex gap-2 flex-wrap">{DIETS.map(d=><button key={d.v} onClick={()=>toggle('dietary_restrictions',d.v)} className={`btn-pill ${preferences.dietary_restrictions.includes(d.v)?'active':''}`}>{d.l}</button>)}</div>
                </div>
                <div>
                  <p className="text-sm font-medium mb-2" style={{color:'var(--color-text-secondary)'}}>Livsstil</p>
                  <div className="flex gap-2 flex-wrap">{LIFESTYLES.map(d=><button key={d.v} onClick={()=>toggle('lifestyle_preferences',d.v)} className={`btn-pill ${(preferences.lifestyle_preferences||[]).includes(d.v)?'active':''}`}>{d.l}</button>)}</div>
                </div>
                <div>
                  <p className="text-sm font-medium mb-2" style={{color:'var(--color-text-secondary)'}}>Undvik</p>
                  <div className="flex gap-1.5 flex-wrap">{DISLIKES.map(d=><button key={d} onClick={()=>toggle('disliked_ingredients',d)} className={`btn-pill text-xs ${preferences.disliked_ingredients.includes(d)?'active-red':''}`}>{d}</button>)}</div>
                </div>
                {preferences.dietary_restrictions.length>0 && <p className="text-xs p-3 rounded-xl" style={{background:'#fffbeb',color:'#92400e'}}>Dubbelkolla alltid ingredienserna vid allergier.</p>}
              </div>
            )}

            <button onClick={goToOffers} disabled={loading} className="btn btn-primary w-full">
              {loading ? 'Hämtar erbjudanden...' : 'Skapa min veckomeny'}
            </button>
          </div>
        </div>
      )}

      {/* === SECTION 3: Därför sparar du === */}
      <section className="card p-6 mb-8">
        <h2 className="text-lg font-bold mb-4">Därför sparar du pengar</h2>
        <div className="grid grid-cols-2 gap-4">
          {[
            {t:'Färre impulsköp',d:'Du vet exakt vad du behöver'},
            {t:'Kampanjvaror som motor',d:'Middagar byggda på det som är billigast'},
            {t:'Tydlig veckokostnad',d:'Se vad veckan kostar innan du handlar'},
            {t:'Smartare planering',d:'Mindre svinn, mer kontroll'},
          ].map(({t,d})=>(
            <div key={t} className="p-3 rounded-xl" style={{background:'var(--color-bg)'}}>
              <p className="text-sm font-semibold">{t}</p>
              <p className="text-xs mt-0.5" style={{color:'var(--color-text-muted)'}}>{d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* === SECTION 4: CTA === */}
      <section className="text-center mb-10">
        <button onClick={goToOffers} disabled={loading} className="btn btn-primary text-lg px-10 py-4">
          Testa Veckosmak gratis
        </button>
        <p className="text-xs mt-3" style={{color:'var(--color-text-muted)'}}>
          1100+ ICA-butiker · 600+ recept med betyg · Helt gratis
        </p>
      </section>

      {/* Email signup */}
      <EmailSignup context="home" />

      {/* Social proof */}
      <section className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm py-6 mb-8 rounded-xl" style={{
        background: 'var(--color-bg)', color: 'var(--color-text-muted)',
        border: '1px solid var(--color-border-light)',
      }}>
        <span><b style={{color:'var(--color-text)'}}>1 286</b> butiker</span>
        <span><b style={{color:'var(--color-text)'}}>1 352</b> recept</span>
        <span><b style={{color:'var(--color-text)'}}>3</b> receptkällor</span>
        <span>Helt gratis</span>
      </section>

      {/* SEO */}
      <section className="space-y-4 text-sm" style={{color:'var(--color-text-muted)'}}>
        <div>
          <h2 className="text-base font-bold mb-1" style={{color:'var(--color-text)'}}>Gör veckans erbjudanden användbara</h2>
          <p>Veckosmak matchar butikens aktuella kampanjer med middagar som passar ditt hushåll. Resultatet är en färdig vecka med recept och inköpslista.</p>
        </div>
        <div>
          <h2 className="text-base font-bold mb-1" style={{color:'var(--color-text)'}}>Se vad veckan kostar</h2>
          <p>Varje meny visar uppskattad kostnad och pris per portion. Du vet vad veckan kostar innan du handlar.</p>
        </div>
      </section>
    </div>
  )
}
