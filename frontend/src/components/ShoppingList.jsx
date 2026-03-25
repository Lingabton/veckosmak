import { useState, useEffect } from 'react'
import { loadChecked, saveChecked } from '../hooks/useMenu'

const CATEGORIES = {
  produce: { name: 'Frukt & grönt', icon: '🥬' },
  meat: { name: 'Kött & chark', icon: '🥩' },
  fish: { name: 'Fisk & skaldjur', icon: '🐟' },
  dairy: { name: 'Mejeri & ägg', icon: '🧀' },
  pantry: { name: 'Skafferi', icon: '🫙' },
  bakery: { name: 'Bröd', icon: '🍞' },
  frozen: { name: 'Fryst', icon: '🧊' },
  other: { name: 'Övrigt', icon: '📦' },
}

const CATEGORY_ORDER = ['produce', 'meat', 'fish', 'dairy', 'pantry', 'bakery', 'frozen', 'other']

export default function ShoppingList({ menu, onBack, copySuccess, onCopy }) {
  const [checked, setChecked] = useState(loadChecked)

  useEffect(() => { saveChecked(checked) }, [checked])

  if (!menu?.shopping_list) return null

  const { items, total_estimated_cost, items_on_offer } = menu.shopping_list
  const savings = menu.total_savings
  const checkedCount = Object.values(checked).filter(Boolean).length
  const progress = items.length > 0 ? (checkedCount / items.length) * 100 : 0

  const toggle = (name) => setChecked(prev => ({ ...prev, [name]: !prev[name] }))

  const grouped = {}
  for (const item of items) {
    const cat = item.category || 'other'
    if (!grouped[cat]) grouped[cat] = []
    grouped[cat].push(item)
  }

  const buildClipboardText = () => {
    const lines = ['Inköpslista — Veckosmak']
    for (const cat of CATEGORY_ORDER) {
      const catItems = grouped[cat]
      if (!catItems) continue
      lines.push(`\n${CATEGORIES[cat]?.name || cat}:`)
      for (const item of catItems) {
        const amount = item.total_amount > 0 ? `${item.total_amount} ${item.unit} ` : ''
        const offer = item.is_on_offer ? ' (erbjudande)' : ''
        lines.push(`  - ${amount}${item.ingredient_name}${offer}`)
      }
    }
    lines.push(`\nUppskattad totalkostnad: ${Math.round(total_estimated_cost)} kr`)
    if (savings > 0) lines.push(`Besparing: ~${Math.round(savings)} kr`)
    return lines.join('\n')
  }

  const handleShare = async () => {
    const text = buildClipboardText()
    if (navigator.share) {
      try { await navigator.share({ title: 'Inköpslista — Veckosmak', text }); return } catch {}
    }
    onCopy(text)
  }

  return (
    <section aria-label="Inköpslista" className="print-section">
      <div className="flex items-center justify-between mb-4 print:hidden">
        <button onClick={onBack} className="text-sm text-gray-500 hover:text-green-700 transition-colors">
          ← Tillbaka
        </button>
        <div className="flex gap-3">
          <button onClick={handleShare}
            className="text-sm font-medium text-green-700 hover:text-green-800 transition-colors">
            {copySuccess ? '✓ Kopierat!' : 'Dela'}
          </button>
          <button onClick={() => window.print()}
            className="text-sm text-gray-500 hover:text-green-700 transition-colors print:hidden">
            Skriv ut
          </button>
        </div>
      </div>

      <h1 className="text-xl font-bold text-gray-900 mb-1">Inköpslista</h1>
      <p className="text-sm text-gray-500 mb-3">Vecka {menu.week_number}, {menu.year}</p>

      {/* Progress bar */}
      <div className="mb-4">
        <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
          <span>{checkedCount} av {items.length} varor</span>
          <span>{items_on_offer} på erbjudande</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2.5">
          <div className="bg-green-600 h-2.5 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }} />
        </div>
        {savings > 0 && (
          <p className="text-xs text-green-600 mt-1">
            Uppskattat: {Math.round(total_estimated_cost)} kr (sparar ~{Math.round(savings)} kr)
          </p>
        )}
      </div>

      <div className="space-y-5">
        {CATEGORY_ORDER.map(cat => {
          const catItems = grouped[cat]
          if (!catItems || catItems.length === 0) return null
          const catInfo = CATEGORIES[cat] || { name: cat, icon: '📦' }
          const catTotal = catItems.reduce((s, i) => s + i.estimated_price, 0)

          return (
            <div key={cat}>
              <div className="flex items-center justify-between mb-2">
                <h2 className="font-semibold text-gray-900 text-sm flex items-center gap-1.5">
                  <span>{catInfo.icon}</span> {catInfo.name}
                </h2>
                <span className="text-xs text-gray-400">~{Math.round(catTotal)} kr</span>
              </div>
              <ul className="space-y-0.5">
                {catItems.map((item, i) => {
                  const isChecked = !!checked[item.ingredient_name]
                  return (
                    <li key={i}
                      onClick={() => toggle(item.ingredient_name)}
                      className={`flex items-center gap-3 py-2.5 px-3 rounded-lg transition-all cursor-pointer ${
                        isChecked ? 'bg-gray-50 opacity-40' : 'bg-white hover:bg-gray-50'
                      } ${isChecked ? 'animate-check' : ''}`}>
                      <input type="checkbox" checked={isChecked} readOnly
                        className="w-5 h-5 rounded border-gray-300 text-green-700 focus:ring-green-700 shrink-0 pointer-events-none" />
                      <div className="flex-1 min-w-0">
                        <span className={`text-sm ${isChecked ? 'line-through text-gray-400' : 'text-gray-900'}`}>
                          {item.total_amount > 0 && <span className="text-gray-500">{item.total_amount} {item.unit} </span>}
                          {item.ingredient_name}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        {item.is_on_offer && (
                          <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded font-medium">🏷️</span>
                        )}
                        <span className="text-sm text-gray-400">~{Math.round(item.estimated_price)} kr</span>
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
