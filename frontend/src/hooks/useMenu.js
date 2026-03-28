import { useState, useCallback, useEffect } from 'react'

const STORAGE_KEY = 'veckosmak_preferences'
const CHECKED_KEY = 'veckosmak_checked'
const MENU_KEY = 'veckosmak_menu'
const HISTORY_KEY = 'veckosmak_history'
const SAVINGS_KEY = 'veckosmak_total_savings'
const HAVE_AT_HOME_KEY = 'veckosmak_have_at_home'

const DEFAULT_PREFS = {
  household_size: 4,
  num_dinners: 5,
  budget_per_week: null,
  max_cook_time: null,
  time_mix: null,
  dietary_restrictions: [],
  lifestyle_preferences: [],
  disliked_ingredients: [],
  pinned_offer_ids: [],
  store_id: 'ica-maxi-1004097',
  has_children: false,
  selected_days: [],
}

function loadPreferences() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) return { ...DEFAULT_PREFS, ...JSON.parse(saved) }
  } catch {}
  return DEFAULT_PREFS
}

function savePreferences(prefs) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs))
}

function getViewFromHash() {
  const hash = window.location.hash.replace('#', '')
  if (hash === 'meny' || hash === 'menu') return 'menu'
  if (hash === 'inkopslista' || hash === 'shopping') return 'shopping'
  if (hash === 'erbjudanden' || hash === 'offers') return 'offers'
  return 'preferences'
}

function setHashForView(view) {
  const hashMap = { preferences: '', menu: 'meny', shopping: 'inkopslista', offers: 'erbjudanden' }
  const newHash = hashMap[view] || ''
  if (newHash) {
    window.history.pushState(null, '', `#${newHash}`)
  } else {
    window.history.pushState(null, '', window.location.pathname)
  }
}

// Menu history — last 10 menus
function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]') } catch { return [] }
}
function saveToHistory(menu) {
  try {
    const history = loadHistory()
    history.unshift({ id: menu.id, date: menu.generated_at, store: menu.store_name, cost: menu.total_cost, savings: menu.total_savings, meals: menu.meals?.length })
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 10)))
  } catch {}
}

// Total savings tracker
function addSavings(amount) {
  try {
    const current = parseFloat(localStorage.getItem(SAVINGS_KEY) || '0')
    localStorage.setItem(SAVINGS_KEY, String(Math.round((current + amount) * 100) / 100))
  } catch {}
}
export function getTotalSavings() {
  try { return parseFloat(localStorage.getItem(SAVINGS_KEY) || '0') } catch { return 0 }
}

// Have at home
export function loadHaveAtHome() {
  try { return JSON.parse(localStorage.getItem(HAVE_AT_HOME_KEY) || '[]') } catch { return [] }
}
export function saveHaveAtHome(items) {
  localStorage.setItem(HAVE_AT_HOME_KEY, JSON.stringify(items))
}

export function loadChecked() {
  try {
    const saved = localStorage.getItem(CHECKED_KEY)
    if (saved) return JSON.parse(saved)
  } catch {}
  return {}
}

export function saveChecked(checked) {
  localStorage.setItem(CHECKED_KEY, JSON.stringify(checked))
}

export function useMenu() {
  const [preferences, setPreferencesState] = useState(loadPreferences)
  const [topOffers, setTopOffers] = useState([])
  const [loading, setLoading] = useState(false)
  const [loadingOffers, setLoadingOffers] = useState(false)
  const [swapping, setSwapping] = useState(null)
  const [error, setError] = useState(null)
  useEffect(() => { setError(null) }, [])
  const [copySuccess, setCopySuccess] = useState(false)
  const [expandAll, setExpandAll] = useState(false)
  const [isReturning] = useState(() => !!localStorage.getItem(STORAGE_KEY))
  const [bonusOffers, setBonusOffers] = useState([])
  const [menuHistory] = useState(loadHistory)
  const [totalSavings, setTotalSavings] = useState(getTotalSavings)

  // Load saved menu from localStorage
  const [menu, setMenuState] = useState(() => {
    try {
      const saved = localStorage.getItem(MENU_KEY)
      return saved ? JSON.parse(saved) : null
    } catch { return null }
  })
  const [hasSavedMenu] = useState(() => !!localStorage.getItem(MENU_KEY))

  // Determine initial view — show menu if we have one saved
  const [view, setViewState] = useState(() => {
    const hash = getViewFromHash()
    if (hash !== 'preferences') return hash
    try {
      const saved = localStorage.getItem(MENU_KEY)
      if (saved) return 'menu'
    } catch {}
    return 'preferences'
  })

  // Wrap setMenu to also save to localStorage
  const setMenu = useCallback((menuOrFn) => {
    setMenuState(prev => {
      const next = typeof menuOrFn === 'function' ? menuOrFn(prev) : menuOrFn
      if (next) {
        try { localStorage.setItem(MENU_KEY, JSON.stringify(next)) } catch {}
      }
      return next
    })
  }, [])

  useEffect(() => {
    const handlePop = () => {
      const v = getViewFromHash()
      if ((v === 'menu' || v === 'shopping') && !menu) {
        setViewState('preferences')
      } else {
        setViewState(v)
      }
    }
    window.addEventListener('popstate', handlePop)
    return () => window.removeEventListener('popstate', handlePop)
  }, [menu])

  const setView = useCallback((v) => {
    setViewState(v)
    setHashForView(v)
    if (v === 'preferences') setError(null) // Clear errors when going back
  }, [])

  const setPreferences = useCallback((prefs) => {
    setPreferencesState(prefs)
    savePreferences(prefs)
  }, [])

  // Ensure offers exist for the selected store, scraping if needed
  const ensureOffers = useCallback(async (storeId) => {
    try {
      const resp = await fetch(`/api/offers?store_id=${storeId}`, { signal: AbortSignal.timeout(45000) })
      const data = resp.ok ? await resp.json() : { count: 0 }
      if (data.count === 0) {
        // No offers — scrape this store
        await fetch(`/api/offers/scrape?store_id=${storeId}`, { method: 'POST', signal: AbortSignal.timeout(30000) })
      }
    } catch {}
  }, [])

  // Fetch top offers
  const fetchTopOffers = useCallback(async () => {
    setLoadingOffers(true)
    try {
      await ensureOffers(preferences.store_id)
      const resp = await fetch(`/api/offers/top?store_id=${preferences.store_id}&limit=10`, { signal: AbortSignal.timeout(10000) })
      const data = resp.ok ? await resp.json() : { offers: [] }
      setTopOffers(data.offers || [])
    } catch {
      setTopOffers([])
    }
    setLoadingOffers(false)
  }, [preferences.store_id, ensureOffers])

  // Go to offers selection step
  const goToOffers = useCallback(async () => {
    await fetchTopOffers()
    setView('offers')
  }, [fetchTopOffers, setView])

  const generateMenu = useCallback(async () => {
    setLoading(true)
    setError(null)
    setExpandAll(false)
    try {
      // Ensure offers exist for selected store
      await ensureOffers(preferences.store_id)

      const resp = await fetch('/api/menu/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preferences),
        signal: AbortSignal.timeout(60000),
      })
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}))
        throw new Error(data.detail || 'Något gick fel. Försök igen.')
      }
      const data = await resp.json()
      setMenu(data)
      saveChecked({})
      localStorage.removeItem('veckosmak_custom_items')
      // Track history and savings
      saveToHistory(data)
      if (data.total_savings > 0) {
        addSavings(data.total_savings)
        setTotalSavings(getTotalSavings())
      }
      // Track menu generation
      window.plausible?.('Menu Generated', { props: { meals: data.meals?.length, savings: Math.round(data.total_savings) } })
      // Fetch bonus offers (non-blocking)
      fetch(`/api/offers/bonus?menu_id=${data.id}&store_id=${preferences.store_id}`)
        .then(r => r.ok ? r.json() : { groups: [] })
        .then(d => setBonusOffers(d.groups || []))
        .catch(() => {})
      setView('menu')
    } catch (e) {
      if (e.name === 'TimeoutError') {
        setError('Det tog för lång tid att skapa menyn. Försök igen om en stund.')
      } else {
        setError(e.message)
      }
    } finally {
      setLoading(false)
    }
  }, [preferences, setView, ensureOffers])

  const swapRecipe = useCallback(async (day, reason = '', recipe_id = '') => {
    if (!menu) return
    setSwapping(day)
    setError(null)
    try {
      const resp = await fetch('/api/menu/swap', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ menu_id: menu.id, day, reason, recipe_id }),
        signal: AbortSignal.timeout(30000),
      })
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}))
        throw new Error(data.detail || 'Kunde inte byta recept. Försök igen.')
      }
      const updatedMenu = await resp.json()
      setMenu(updatedMenu)
      window.plausible?.('Recipe Swapped', { props: { day } })
    } catch (e) {
      if (e.name === 'TimeoutError') {
        setError('Det tog för lång tid att byta recept. Försök igen.')
      } else {
        setError(e.message)
      }
    } finally {
      setSwapping(null)
    }
  }, [menu])

  const sendFeedback = useCallback(async (day, action) => {
    if (!menu) return
    try {
      await fetch('/api/menu/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ menu_id: menu.id, day, action }),
      })
    } catch {}
  }, [menu])

  const copyToClipboard = useCallback(async (text) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopySuccess(true)
      setTimeout(() => setCopySuccess(false), 2000)
    } catch {}
  }, [])

  return {
    preferences, setPreferences,
    menu, topOffers, loading, loadingOffers, swapping, error,
    view, setView,
    generateMenu, goToOffers, swapRecipe, sendFeedback,
    copySuccess, copyToClipboard,
    expandAll, setExpandAll,
    isReturning, bonusOffers,
    menuHistory, totalSavings,
  }
}
