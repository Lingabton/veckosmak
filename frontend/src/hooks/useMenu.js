import { useState, useCallback, useEffect } from 'react'

const STORAGE_KEY = 'veckosmak_preferences'
const CHECKED_KEY = 'veckosmak_checked'

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
  const [menu, setMenu] = useState(null)
  const [topOffers, setTopOffers] = useState([])
  const [loading, setLoading] = useState(false)
  const [loadingOffers, setLoadingOffers] = useState(false)
  const [swapping, setSwapping] = useState(null)
  const [error, setError] = useState(null)
  const [view, setViewState] = useState('preferences')
  const [copySuccess, setCopySuccess] = useState(false)
  const [expandAll, setExpandAll] = useState(false)
  const [isReturning] = useState(() => !!localStorage.getItem(STORAGE_KEY))
  const [bonusOffers, setBonusOffers] = useState([])

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
  }, [])

  const setPreferences = useCallback((prefs) => {
    setPreferencesState(prefs)
    savePreferences(prefs)
  }, [])

  // Fetch top offers with timeout
  const fetchTopOffers = useCallback(async () => {
    setLoadingOffers(true)
    try {
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 8000)
      const resp = await fetch(`/api/offers/top?store_id=${preferences.store_id}&limit=10`, {
        signal: controller.signal,
      })
      clearTimeout(timeout)
      if (resp.ok) {
        const data = await resp.json()
        setTopOffers(data.offers || [])
      } else {
        setTopOffers([])
      }
    } catch (e) {
      // Timeout or network error — proceed with empty offers
      setTopOffers([])
    }
    setLoadingOffers(false)
  }, [preferences.store_id])

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
      const resp = await fetch('/api/menu/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preferences),
      })
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}))
        throw new Error(data.detail || 'Något gick fel. Försök igen.')
      }
      const data = await resp.json()
      setMenu(data)
      saveChecked({})
      // Fetch bonus offers (non-blocking)
      fetch(`/api/offers/bonus?menu_id=${data.id}&store_id=${preferences.store_id}`)
        .then(r => r.ok ? r.json() : { offers: [] })
        .then(d => setBonusOffers(d.offers || []))
        .catch(() => {})
      setView('menu')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [preferences, setView])

  const swapRecipe = useCallback(async (day, reason = '') => {
    if (!menu) return
    setSwapping(day)
    setError(null)
    try {
      const resp = await fetch('/api/menu/swap', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ menu_id: menu.id, day, reason }),
      })
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}))
        throw new Error(data.detail || 'Kunde inte byta recept. Försök igen.')
      }
      // Backend now returns full updated menu (with rebuilt shopping list)
      const updatedMenu = await resp.json()
      setMenu(updatedMenu)
    } catch (e) {
      setError(e.message)
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
  }
}
