import { useState, useEffect, useCallback } from 'react'

const DIET_COLORS = {
  vegetarisk: { bg: '#d8f3dc', color: '#1b4332' },
  vegan: { bg: '#d8f3dc', color: '#1b4332' },
  glutenfri: { bg: '#fff3cd', color: '#856404' },
  laktosfri: { bg: '#cfe2ff', color: '#084298' },
  barnvänlig: { bg: '#fef3c7', color: '#92400e' },
}

function MenuCard({ menu, onLike, onExpand, expanded, userEmail }) {
  const [liking, setLiking] = useState(false)

  const handleLike = async (e) => {
    e.stopPropagation()
    if (!userEmail || liking) return
    setLiking(true)
    await onLike(menu.id)
    setLiking(false)
  }

  return (
    <article className={`card card-interactive overflow-hidden fade-up`}>
      <div className="cursor-pointer p-5" onClick={() => onExpand(menu.id)}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="font-bold text-base leading-snug truncate">{menu.title}</h3>
            <div className="flex items-center gap-2 mt-1 text-xs" style={{ color: 'var(--color-text-muted)' }}>
              {menu.city && <span>{menu.city}</span>}
              <span>{menu.num_meals} middagar</span>
            </div>
          </div>
          <button
            onClick={handleLike}
            disabled={!userEmail || liking}
            className="shrink-0 flex items-center gap-1 text-sm transition-all"
            style={{
              color: menu.user_liked ? 'var(--color-accent)' : 'var(--color-text-muted)',
              opacity: !userEmail ? 0.4 : 1,
              cursor: !userEmail ? 'default' : 'pointer',
            }}
            title={!userEmail ? 'Logga in för att gilla' : ''}
          >
            <span className="text-base">{menu.user_liked ? '❤️' : '🤍'}</span>
            <span className="font-medium">{menu.likes || 0}</span>
          </button>
        </div>

        <div className="flex items-center gap-3 mt-3">
          <span className="text-lg font-bold" style={{ color: 'var(--color-accent)' }}>
            {Math.round(menu.total_cost)} kr
          </span>
          {menu.savings > 0 && (
            <span className="text-xs font-semibold" style={{ color: 'var(--color-brand)' }}>
              −{Math.round(menu.savings)} kr besparing
            </span>
          )}
        </div>

        {menu.dietary_tags && menu.dietary_tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {menu.dietary_tags.map(tag => {
              const colors = DIET_COLORS[tag] || { bg: 'var(--color-border-light)', color: 'var(--color-text-secondary)' }
              return (
                <span key={tag} className="text-xs px-2 py-0.5 rounded-full font-medium"
                  style={{ background: colors.bg, color: colors.color }}>
                  {tag}
                </span>
              )
            })}
          </div>
        )}

        <div className="flex items-center justify-end mt-2">
          <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
            {expanded ? '▲ Dölj' : '▼ Visa meny'}
          </span>
        </div>
      </div>

      {expanded && (
        <div className="px-5 pb-5 expand" style={{ borderTop: '1px solid var(--color-border-light)' }}>
          {menu.description && (
            <p className="text-sm mt-4 mb-3" style={{ color: 'var(--color-text-secondary)' }}>
              {menu.description}
            </p>
          )}
          {menu.meals && menu.meals.length > 0 ? (
            <div className="space-y-2 mt-3">
              {menu.meals.map((meal, i) => (
                <div key={i} className="flex items-center justify-between text-sm py-2 px-3 rounded-lg"
                  style={{ background: 'var(--color-bg)' }}>
                  <div>
                    <span className="font-medium">{meal.recipe?.title || meal.title}</span>
                    {meal.recipe?.cook_time_minutes && (
                      <span className="text-xs ml-2" style={{ color: 'var(--color-text-muted)' }}>
                        {meal.recipe.cook_time_minutes} min
                      </span>
                    )}
                  </div>
                  {meal.estimated_cost && (
                    <span className="font-bold shrink-0 ml-2" style={{ color: 'var(--color-accent)' }}>
                      {Math.round(meal.estimated_cost)} kr
                    </span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm mt-3" style={{ color: 'var(--color-text-muted)' }}>
              Inga detaljer tillgängliga.
            </p>
          )}
        </div>
      )}
    </article>
  )
}

export default function CommunityPage({ userEmail, onShareClick }) {
  const [menus, setMenus] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [sort, setSort] = useState('popular')
  const [city, setCity] = useState('')
  const [expandedId, setExpandedId] = useState(null)
  const [expandedDetails, setExpandedDetails] = useState({})

  const fetchMenus = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ sort, limit: '10' })
      if (city.trim()) params.set('city', city.trim())
      const resp = await fetch(`/api/community/menus?${params}`)
      if (!resp.ok) throw new Error('Kunde inte hämta menyer')
      const data = await resp.json()
      setMenus(data.menus || data || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [sort, city])

  useEffect(() => {
    fetchMenus()
  }, [fetchMenus])

  const handleLike = async (menuId) => {
    if (!userEmail) return
    try {
      const resp = await fetch(`/api/community/menu/${menuId}/like`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: userEmail }),
      })
      if (resp.ok) {
        setMenus(prev => prev.map(m =>
          m.id === menuId
            ? { ...m, likes: m.user_liked ? m.likes - 1 : m.likes + 1, user_liked: !m.user_liked }
            : m
        ))
      }
    } catch {}
  }

  const handleExpand = async (menuId) => {
    if (expandedId === menuId) {
      setExpandedId(null)
      return
    }
    setExpandedId(menuId)

    if (!expandedDetails[menuId]) {
      try {
        const resp = await fetch(`/api/community/menu/${menuId}`)
        if (resp.ok) {
          const data = await resp.json()
          setExpandedDetails(prev => ({ ...prev, [menuId]: data }))
          setMenus(prev => prev.map(m => m.id === menuId ? { ...m, ...data } : m))
        }
      } catch {}
    }
  }

  return (
    <section className="fade-in">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Menyer från andra</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--color-text-muted)' }}>
            Inspiration och sparidéer från andra familjer
          </p>
        </div>
        {onShareClick && (
          <button onClick={onShareClick} className="btn btn-primary text-sm px-4 py-2 shrink-0">
            Dela din meny
          </button>
        )}
      </div>

      {/* Sort tabs */}
      <div className="flex items-center gap-2 mb-4">
        {[['popular', 'Populära'], ['recent', 'Senaste']].map(([value, label]) => (
          <button
            key={value}
            onClick={() => setSort(value)}
            className={`btn-pill ${sort === value ? 'active' : ''}`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* City filter */}
      <div className="mb-6">
        <input
          type="text"
          value={city}
          onChange={e => setCity(e.target.value)}
          placeholder="Filtrera på stad (valfritt)"
          className="w-full sm:w-64 px-4 py-2.5 text-sm border rounded-lg outline-none focus:ring-2 focus:ring-green-700"
          style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface)' }}
        />
      </div>

      {/* Error */}
      {error && (
        <div className="card p-4 mb-6 fade-in" style={{ background: '#fff5f5', borderColor: '#ffc9c9' }}>
          <p className="text-sm" style={{ color: '#c92a2a' }}>{error}</p>
          <button onClick={fetchMenus} className="text-sm font-medium mt-2 underline" style={{ color: '#c92a2a' }}>
            Försök igen
          </button>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="text-center py-16 fade-in">
          <div className="w-8 h-8 border-2 rounded-full animate-spin mx-auto mb-4"
            style={{ borderColor: 'var(--color-border)', borderTopColor: 'var(--color-brand)' }} />
          <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Laddar menyer...</p>
        </div>
      )}

      {/* Menu grid */}
      {!loading && !error && menus.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2">
          {menus.map((menu, i) => (
            <MenuCard
              key={menu.id}
              menu={menu}
              onLike={handleLike}
              onExpand={handleExpand}
              expanded={expandedId === menu.id}
              userEmail={userEmail}
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && menus.length === 0 && (
        <div className="text-center py-16 fade-in">
          <p className="text-4xl mb-4">📋</p>
          <h2 className="text-lg font-bold mb-2">Inga menyer ännu</h2>
          <p className="text-sm mb-6" style={{ color: 'var(--color-text-muted)' }}>
            {city.trim()
              ? `Inga delade menyer hittades i ${city}. Prova en annan stad eller ta bort filtret.`
              : 'Bli den första att dela en veckomeny med communityn!'}
          </p>
          {onShareClick && (
            <button onClick={onShareClick} className="btn btn-primary">Dela din meny</button>
          )}
        </div>
      )}
    </section>
  )
}
