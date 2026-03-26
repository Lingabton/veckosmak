import { useState, useEffect } from 'react'
import { loadChecked, saveChecked, loadHaveAtHome, saveHaveAtHome } from '../hooks/useMenu'

const CATEGORIES = {
  produce: 'Frukt & grönt', meat: 'Kött & chark', fish: 'Fisk & skaldjur',
  dairy: 'Mejeri & ägg', pantry: 'Skafferi', bakery: 'Bröd', frozen: 'Fryst',
  other: 'Övrigt', custom: 'Mina tillägg',
}
const CATEGORY_ORDER = ['bakery', 'meat', 'fish', 'produce', 'dairy', 'pantry', 'frozen', 'other', 'custom']

const CUSTOM_KEY = 'veckosmak_custom_items'
function loadCustom() { try { return JSON.parse(localStorage.getItem(CUSTOM_KEY) || '[]') } catch { return [] } }
function saveCustom(items) { localStorage.setItem(CUSTOM_KEY, JSON.stringify(items)) }

const QUICK_ADD = ['Mjölk', 'Bröd', 'Ägg', 'Bananer', 'Kaffe', 'Smör', 'Juice', 'Yoghurt', 'Ost', 'Toapapper']
const CAT_COLORS = {
  bakery: '#92400e', meat: '#991b1b', fish: '#1e40af', produce: '#166534',
  dairy: '#4338ca', pantry: '#78350f', frozen: '#0e7490', other: '#6b7280',
}

export default function ShoppingList({ menu, onBack, copySuccess, onCopy }) {
  const [checked, setChecked] = useState(loadChecked)
  const [customItems, setCustomItems] = useState(loadCustom)
  const [haveAtHome, setHaveAtHome] = useState(loadHaveAtHome)
  const [newItem, setNewItem] = useState('')
  const [showHaveAtHome, setShowHaveAtHome] = useState(false)
  useEffect(() => { saveChecked(checked) }, [checked])
  useEffect(() => { saveCustom(customItems) }, [customItems])
  useEffect(() => { saveHaveAtHome(haveAtHome) }, [haveAtHome])
  if (!menu?.shopping_list) return null

  const addCustom = (name) => {
    if (!name.trim() || customItems.includes(name.trim())) return
    setCustomItems([...customItems, name.trim()])
    setNewItem('')
  }
  const removeCustom = (name) => {
    setCustomItems(customItems.filter(i => i !== name))
    setChecked(prev => { const n = {...prev}; delete n[`custom:${name}`]; return n })
  }

  const { items, total_estimated_cost, items_on_offer } = menu.shopping_list
  const homeSet = new Set(haveAtHome.map(h => h.toLowerCase()))
  const filteredItems = items.filter(i => !homeSet.has(i.ingredient_name.toLowerCase()))
  const allItems = [...filteredItems, ...customItems.map(name => ({
    ingredient_name: name, total_amount: 0, unit: '', category: 'custom',
    estimated_price: 0, is_on_offer: false, matched_offer: null, used_in: [],
  }))]
  const checkedCount = Object.values(checked).filter(Boolean).length
  const totalCount = allItems.length
  const progress = totalCount > 0 ? (checkedCount / totalCount) * 100 : 0
  const remainingCost = items.reduce((sum, i) => checked[i.ingredient_name] ? sum : sum + i.estimated_price, 0)
  const toggle = (name) => setChecked(prev => ({ ...prev, [name]: !prev[name] }))

  const grouped = {}
  for (const item of allItems) {
    const cat = item.category || 'other'
    if (!grouped[cat]) grouped[cat] = []
    grouped[cat].push(item)
  }

  const buildText = () => {
    const lines = ['Inköpslista — Veckosmak\n']
    for (const cat of CATEGORY_ORDER) {
      if (!grouped[cat]) continue
      lines.push(`${CATEGORIES[cat]}:`)
      for (const item of grouped[cat]) {
        const a = item.total_amount > 0 ? `${item.total_amount} ${item.unit} ` : ''
        lines.push(`  ${a}${item.ingredient_name}${item.is_on_offer ? ' *' : ''}`)
      }
      lines.push('')
    }
    lines.push(`Uppskattad kostnad: ${Math.round(total_estimated_cost)} kr`)
    return lines.join('\n')
  }

  const handleShare = async () => {
    const text = buildText()
    if (navigator.share) { try { await navigator.share({ title: 'Inköpslista', text }); return } catch {} }
    onCopy(text)
  }

  return (
    <section className="animate-fade-in">
      <div className="flex items-center justify-between mb-6 print:hidden">
        <button onClick={onBack} className="text-sm" style={{ color: 'var(--text-muted)' }}>Tillbaka</button>
        <div className="flex gap-4">
          <button onClick={handleShare} className="text-sm font-medium" style={{ color: 'var(--green)' }}>
            {copySuccess ? 'Kopierat' : 'Dela'}
          </button>
          <button onClick={() => window.print()} className="text-sm print:hidden" style={{ color: 'var(--text-muted)' }}>Skriv ut</button>
        </div>
      </div>

      <h1 className="text-2xl font-bold tracking-tight mb-1">Inköpslista</h1>
      <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>
        {menu.date_range || `Vecka ${menu.week_number}`} — {items_on_offer} erbjudanden
      </p>

      {/* Progress + remaining cost */}
      <div className="mb-6">
        <div className="flex justify-between text-xs mb-1.5" style={{ color: 'var(--text-muted)' }}>
          <span>{checkedCount} av {items.length} varor</span>
          <span>
            {checkedCount > 0 && checkedCount < items.length
              ? `~${Math.round(remainingCost)} kr kvar`
              : `~${Math.round(total_estimated_cost)} kr totalt`
            }
          </span>
        </div>
        <div className="w-full rounded-full h-2" style={{ backgroundColor: 'var(--color-border)' }}>
          <div className="h-2 rounded-full transition-all duration-300" style={{ width: `${progress}%`, backgroundColor: 'var(--color-brand)' }} />
        </div>
        {checkedCount === totalCount && totalCount > 0 && (
          <div className="text-center mt-3 p-4 rounded-xl fade-in" style={{background:'var(--color-brand-light)'}}>
            <p className="text-2xl mb-1">🎉</p>
            <p className="font-bold" style={{color:'var(--color-brand-dark)'}}>Klart! Allt avbockat.</p>
            <p className="text-xs mt-1" style={{color:'var(--color-brand)'}}>Bra handlat!</p>
          </div>
        )}
      </div>

      <div className="space-y-6">
        {CATEGORY_ORDER.map(cat => {
          const catItems = grouped[cat]
          if (!catItems?.length) return null
          const catTotal = catItems.reduce((s, i) => s + i.estimated_price, 0)
          const catColor = CAT_COLORS[cat] || 'var(--text-secondary)'

          return (
            <div key={cat}>
              <div className="flex justify-between items-center mb-2">
                <h2 className="text-sm font-semibold uppercase tracking-wider" style={{ color: catColor }}>
                  {CATEGORIES[cat]}
                </h2>
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>~{Math.round(catTotal)} kr</span>
              </div>
              <div className="rounded-xl border overflow-hidden" style={{ borderColor: 'var(--border)' }}>
                {catItems.map((item, i) => {
                  const isChecked = !!checked[item.ingredient_name]
                  return (
                    <div key={i} onClick={() => toggle(item.ingredient_name)}
                      className={`flex items-center gap-3 py-3 px-3.5 cursor-pointer transition-all ${
                        i > 0 ? 'border-t' : ''
                      } ${isChecked ? 'opacity-35' : ''}`}
                      style={{
                        backgroundColor: isChecked ? 'var(--bg)' : 'var(--surface)',
                        borderColor: 'var(--border-light)',
                      }}>
                      <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 transition-all ${
                        isChecked ? 'border-green-600 bg-green-600' : ''
                      }`} style={!isChecked ? { borderColor: 'var(--border)' } : {}}>
                        {isChecked && <span className="text-white text-xs">✓</span>}
                      </div>
                      <div className={`flex-1 min-w-0 ${isChecked ? 'line-through' : ''}`}>
                        <span className="text-sm">
                          {item.total_amount > 0 && <span style={{ color: 'var(--text-muted)' }}>{item.total_amount} {item.unit} </span>}
                          {item.ingredient_name}
                        </span>
                        {item.is_on_offer && item.matched_offer && (
                          <p className="text-xs mt-0.5" style={{ color: 'var(--green)' }}>
                            {item.matched_offer.product_name}
                            {item.matched_offer.brand && <span style={{ color: 'var(--text-muted)' }}> — {item.matched_offer.brand}</span>}
                            {item.matched_offer.quantity_deal && <span> ({item.matched_offer.quantity_deal})</span>}
                          </p>
                        )}
                        {item.used_in && item.used_in.length > 0 && (
                          <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                            {item.used_in.join(', ')}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        {item.is_on_offer && (
                          <span className="text-xs font-medium px-2 py-0.5 rounded-full"
                            style={{ backgroundColor: 'var(--green-soft)', color: 'var(--green)' }}>
                            {item.matched_offer ? `${Math.round(item.matched_offer.offer_price)} ${item.matched_offer.unit}` : 'Erbjudande'}
                          </span>
                        )}
                        {item.estimated_price > 0 && <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>~{Math.round(item.estimated_price)} kr</span>}
                        {item.category === 'custom' && (
                          <button onClick={e => { e.stopPropagation(); removeCustom(item.ingredient_name) }}
                            className="text-xs px-1.5" style={{ color: 'var(--color-text-muted)' }}>✕</button>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>

      {/* Have at home — exclude from list */}
      <div className="mt-6">
        <button onClick={() => setShowHaveAtHome(!showHaveAtHome)}
          className="text-sm font-medium" style={{color:'var(--color-text-muted)'}}>
          {showHaveAtHome ? 'Dölj "Har hemma" ▲' : `Har hemma${haveAtHome.length ? ` (${haveAtHome.length})`:''} ▼`}
        </button>
        {showHaveAtHome && (
          <div className="card p-4 mt-2 expand">
            <p className="text-xs mb-2" style={{color:'var(--color-text-muted)'}}>
              Ingredienser du redan har — dras av från listan
            </p>
            {haveAtHome.length > 0 && (
              <div className="flex gap-1.5 flex-wrap mb-2">
                {haveAtHome.map(item => (
                  <span key={item} className="btn-pill text-xs active flex items-center gap-1">
                    {item}
                    <button onClick={() => setHaveAtHome(haveAtHome.filter(h => h !== item))} className="ml-0.5">✕</button>
                  </span>
                ))}
              </div>
            )}
            <div className="flex gap-1.5 flex-wrap">
              {['Ris','Pasta','Olivolja','Mjöl','Ströbröd','Potatis','Lök','Vitlök','Smör'].filter(i => !haveAtHome.includes(i)).slice(0,6).map(item => (
                <button key={item} onClick={() => setHaveAtHome([...haveAtHome, item])}
                  className="btn-pill text-xs">{item}</button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Add custom items */}
      <div className="mt-4 card p-4">
        <p className="font-bold text-sm mb-3">Lägg till egna varor</p>
        <div className="flex gap-1.5 flex-wrap mb-3">
          {QUICK_ADD.filter(q => !customItems.includes(q)).slice(0, 6).map(q => (
            <button key={q} onClick={() => addCustom(q)}
              className="btn-pill text-xs">{q}</button>
          ))}
        </div>
        <div className="flex gap-2">
          <input type="text" value={newItem} onChange={e => setNewItem(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addCustom(newItem)}
            placeholder="Skriv vara..."
            className="flex-1 px-3 py-2 text-sm border rounded-lg outline-none focus:ring-2 focus:ring-green-700"
            style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg)' }} />
          <button onClick={() => addCustom(newItem)} className="btn btn-primary text-sm px-4 py-2">
            Lägg till
          </button>
        </div>
      </div>
    </section>
  )
}
