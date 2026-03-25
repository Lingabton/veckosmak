import { useState, useEffect } from 'react'
import { loadChecked, saveChecked } from '../hooks/useMenu'

const CATEGORY_NAMES = {
  produce: 'Frukt & grönt',
  meat: 'Kött & chark',
  fish: 'Fisk & skaldjur',
  dairy: 'Mejeri & ägg',
  pantry: 'Skafferi',
  bakery: 'Bröd',
  frozen: 'Fryst',
  other: 'Övrigt',
}

const CATEGORY_ORDER = ['produce', 'meat', 'fish', 'dairy', 'pantry', 'bakery', 'frozen', 'other']

export default function ShoppingList({ menu, onBack, copySuccess, onCopy }) {
  const [checked, setChecked] = useState(loadChecked)

  // Persist checkboxes
  useEffect(() => {
    saveChecked(checked)
  }, [checked])

  if (!menu?.shopping_list) return null

  const { items, total_estimated_cost, items_on_offer } = menu.shopping_list
  const savings = menu.total_savings
  const checkedCount = Object.values(checked).filter(Boolean).length

  const toggle = (name) => {
    setChecked(prev => ({ ...prev, [name]: !prev[name] }))
  }

  // Group items by category
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
      lines.push(`\n${CATEGORY_NAMES[cat] || cat}:`)
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
      try {
        await navigator.share({ title: 'Inköpslista — Veckosmak', text })
        return
      } catch {}
    }
    onCopy(text)
  }

  return (
    <section aria-label="Inköpslista" className="print-section">
      <div className="flex items-center justify-between mb-4 print:hidden">
        <button
          onClick={onBack}
          className="text-sm text-gray-500 hover:text-green-700 transition-colors"
        >
          ← Tillbaka till menyn
        </button>
        <div className="flex gap-3">
          <button
            onClick={handleShare}
            className="text-sm font-medium text-green-700 hover:text-green-800 transition-colors"
            aria-label="Dela inköpslistan"
          >
            {copySuccess ? 'Kopierat!' : 'Dela / Kopiera'}
          </button>
          <button
            onClick={() => window.print()}
            className="text-sm text-gray-500 hover:text-green-700 transition-colors"
            aria-label="Skriv ut inköpslistan"
          >
            Skriv ut
          </button>
        </div>
      </div>

      <h1 className="text-xl font-bold text-gray-900 mb-1">Inköpslista</h1>
      <p className="text-sm text-gray-500 mb-4 print:mb-2">
        Vecka {menu.week_number}, {menu.year}
      </p>

      <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-green-800 font-semibold">
              {items.length} varor, {items_on_offer} på erbjudande
              {checkedCount > 0 && (
                <span className="text-green-600 font-normal ml-2">
                  ({checkedCount} avbockade)
                </span>
              )}
            </p>
            <p className="text-green-600 text-sm">
              Uppskattat totalt: {Math.round(total_estimated_cost)} kr
              {savings > 0 && ` (sparar ca ${Math.round(savings)} kr)`}
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        {CATEGORY_ORDER.map(cat => {
          const catItems = grouped[cat]
          if (!catItems || catItems.length === 0) return null

          return (
            <div key={cat}>
              <div className="flex items-center justify-between mb-2">
                <h2 className="font-semibold text-gray-900 text-sm uppercase tracking-wide">
                  {CATEGORY_NAMES[cat] || cat}
                </h2>
                <span className="text-xs text-gray-400">
                  ~{Math.round(catItems.reduce((s, i) => s + i.estimated_price, 0))} kr
                </span>
              </div>
              <ul className="space-y-1">
                {catItems.map((item, i) => (
                  <li
                    key={i}
                    className={`flex items-center gap-3 py-2.5 px-3 rounded-lg transition-colors ${
                      checked[item.ingredient_name] ? 'bg-gray-50 opacity-50' : 'bg-white'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={!!checked[item.ingredient_name]}
                      onChange={() => toggle(item.ingredient_name)}
                      className="w-5 h-5 rounded border-gray-300 text-green-700 focus:ring-green-700 shrink-0"
                      aria-label={`Markera ${item.ingredient_name}`}
                    />
                    <div className="flex-1 min-w-0">
                      <span className={`text-sm ${checked[item.ingredient_name] ? 'line-through text-gray-400' : 'text-gray-900'}`}>
                        {item.total_amount > 0 && (
                          <span className="text-gray-500">{item.total_amount} {item.unit} </span>
                        )}
                        {item.ingredient_name}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {item.is_on_offer && (
                        <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded font-medium">
                          Erbjudande
                        </span>
                      )}
                      <span className="text-sm text-gray-400">
                        ~{Math.round(item.estimated_price)} kr
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </div>
    </section>
  )
}
