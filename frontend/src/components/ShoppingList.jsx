import { useState, useEffect } from 'react'
import { loadChecked, saveChecked } from '../hooks/useMenu'

const CATEGORIES = {
  produce: 'Frukt & grönt', meat: 'Kött & chark', fish: 'Fisk & skaldjur',
  dairy: 'Mejeri & ägg', pantry: 'Skafferi', bakery: 'Bröd', frozen: 'Fryst', other: 'Övrigt',
}
// Order matches ICA Maxi Boglundsängen, Örebro store layout
const CATEGORY_ORDER = ['bakery', 'meat', 'fish', 'produce', 'dairy', 'pantry', 'frozen', 'other']

export default function ShoppingList({ menu, onBack, copySuccess, onCopy }) {
  const [checked, setChecked] = useState(loadChecked)
  useEffect(() => { saveChecked(checked) }, [checked])
  if (!menu?.shopping_list) return null

  const { items, total_estimated_cost, items_on_offer } = menu.shopping_list
  const checkedCount = Object.values(checked).filter(Boolean).length
  const progress = items.length > 0 ? (checkedCount / items.length) * 100 : 0
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
    <section className="animate-fade-in print-section">
      <div className="flex items-center justify-between mb-6 print:hidden">
        <button onClick={onBack} className="text-sm" style={{ color: 'var(--text-muted)' }}>Tillbaka</button>
        <div className="flex gap-4">
          <button onClick={handleShare} className="text-sm font-medium" style={{ color: 'var(--green)' }}>
            {copySuccess ? 'Kopierat' : 'Dela'}
          </button>
          <button onClick={() => window.print()} className="text-sm print:hidden" style={{ color: 'var(--text-muted)' }}>
            Skriv ut
          </button>
        </div>
      </div>

      <h1 className="text-2xl font-bold tracking-tight mb-1">Inköpslista</h1>
      <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>
        Vecka {menu.week_number} — {items_on_offer} varor på erbjudande
      </p>

      {/* Progress */}
      <div className="mb-6">
        <div className="flex justify-between text-xs mb-1" style={{ color: 'var(--text-muted)' }}>
          <span>{checkedCount} av {items.length}</span>
          <span>{Math.round(total_estimated_cost)} kr</span>
        </div>
        <div className="w-full rounded-full h-2" style={{ backgroundColor: 'var(--border)' }}>
          <div className="h-2 rounded-full transition-all duration-300" style={{ width: `${progress}%`, backgroundColor: 'var(--green)' }} />
        </div>
      </div>

      <div className="space-y-6">
        {CATEGORY_ORDER.map(cat => {
          const catItems = grouped[cat]
          if (!catItems?.length) return null
          const catTotal = catItems.reduce((s, i) => s + i.estimated_price, 0)
          return (
            <div key={cat}>
              <div className="flex justify-between items-center mb-2">
                <h2 className="text-sm font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
                  {CATEGORIES[cat]}
                </h2>
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>~{Math.round(catTotal)} kr</span>
              </div>
              <ul className="space-y-0.5">
                {catItems.map((item, i) => {
                  const isChecked = !!checked[item.ingredient_name]
                  return (
                    <li key={i} onClick={() => toggle(item.ingredient_name)}
                      className={`flex items-center gap-3 py-2.5 px-3 rounded-xl cursor-pointer transition-all ${
                        isChecked ? 'opacity-35' : ''
                      }`}
                      style={{ backgroundColor: isChecked ? 'var(--bg)' : 'var(--surface)' }}>
                      <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 transition-all ${
                        isChecked ? 'border-green-600 bg-green-600' : ''
                      }`} style={!isChecked ? { borderColor: 'var(--border)' } : {}}>
                        {isChecked && <span className="text-white text-xs">✓</span>}
                      </div>
                      <span className={`text-sm flex-1 ${isChecked ? 'line-through' : ''}`}
                        style={{ color: isChecked ? 'var(--text-muted)' : 'var(--text)' }}>
                        {item.total_amount > 0 && <span style={{ color: 'var(--text-muted)' }}>{item.total_amount} {item.unit} </span>}
                        {item.ingredient_name}
                      </span>
                      <div className="flex items-center gap-2 shrink-0">
                        {item.is_on_offer && (
                          <span className="text-xs font-medium px-2 py-0.5 rounded-full" style={{ backgroundColor: 'var(--green-soft)', color: 'var(--green)' }}>
                            Erbjudande
                          </span>
                        )}
                        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>~{Math.round(item.estimated_price)} kr</span>
                      </div>
                    </li>
                  )
                })}
              </ul>
            </div>
          )
        })}
      </div>
    </section>
  )
}
