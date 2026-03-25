import { useState, useEffect } from 'react'
import { loadChecked, saveChecked } from '../hooks/useMenu'

const CATEGORIES = {
  produce: 'Frukt & grönt', meat: 'Kött & chark', fish: 'Fisk & skaldjur',
  dairy: 'Mejeri & ägg', pantry: 'Skafferi', bakery: 'Bröd', frozen: 'Fryst', other: 'Övrigt',
}
// ICA Maxi Boglundsängen layout
const CATEGORY_ORDER = ['bakery', 'meat', 'fish', 'produce', 'dairy', 'pantry', 'frozen', 'other']
const CAT_COLORS = {
  bakery: '#92400e', meat: '#991b1b', fish: '#1e40af', produce: '#166534',
  dairy: '#4338ca', pantry: '#78350f', frozen: '#0e7490', other: '#6b7280',
}

export default function ShoppingList({ menu, onBack, copySuccess, onCopy }) {
  const [checked, setChecked] = useState(loadChecked)
  useEffect(() => { saveChecked(checked) }, [checked])
  if (!menu?.shopping_list) return null

  const { items, total_estimated_cost, items_on_offer } = menu.shopping_list
  const checkedCount = Object.values(checked).filter(Boolean).length
  const progress = items.length > 0 ? (checkedCount / items.length) * 100 : 0
  const remainingCost = items.reduce((sum, i) => checked[i.ingredient_name] ? sum : sum + i.estimated_price, 0)
  const toggle = (name) => setChecked(prev => ({ ...prev, [name]: !prev[name] }))

  const grouped = {}
  for (const item of items) {
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
        <div className="w-full rounded-full h-2" style={{ backgroundColor: 'var(--border)' }}>
          <div className="h-2 rounded-full transition-all duration-300" style={{ width: `${progress}%`, backgroundColor: 'var(--green)' }} />
        </div>
        {checkedCount === items.length && items.length > 0 && (
          <p className="text-sm font-medium mt-2 text-center" style={{ color: 'var(--green)' }}>
            Klart! Allt avbockat.
          </p>
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
                        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>~{Math.round(item.estimated_price)} kr</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
