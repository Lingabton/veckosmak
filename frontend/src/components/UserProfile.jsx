import { useState, useEffect, useCallback } from 'react'

const TIER_BADGES = {
  free: { label: 'Gratis', bg: 'var(--color-border-light)', color: 'var(--color-text-secondary)' },
  premium: { label: 'Premium', bg: 'var(--color-brand-light)', color: 'var(--color-brand-dark)' },
  family: { label: 'Familj', bg: 'var(--color-accent-light)', color: 'var(--color-accent-dark)' },
}

export default function UserProfile({ userEmail, onBack }) {
  const [profile, setProfile] = useState(null)
  const [menus, setMenus] = useState([])
  const [favorites, setFavorites] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState({ name: '', city: '', bio: '', is_public: false })
  const [saving, setSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)

  const [tab, setTab] = useState('history')

  const fetchData = useCallback(async () => {
    if (!userEmail) return
    setLoading(true)
    setError(null)
    try {
      const [profileResp, menusResp, favsResp] = await Promise.all([
        fetch(`/api/user/profile?email=${encodeURIComponent(userEmail)}`),
        fetch(`/api/user/menus?email=${encodeURIComponent(userEmail)}`),
        fetch(`/api/user/favorites?email=${encodeURIComponent(userEmail)}`),
      ])
      if (!profileResp.ok) throw new Error('Kunde inte hämta profil')
      const profileData = await profileResp.json()
      setProfile(profileData)
      setEditForm({
        name: profileData.name || '',
        city: profileData.city || '',
        bio: profileData.bio || '',
        is_public: profileData.is_public || false,
      })
      if (menusResp.ok) {
        const menusData = await menusResp.json()
        setMenus(menusData.menus || menusData || [])
      }
      if (favsResp.ok) {
        const favsData = await favsResp.json()
        setFavorites(favsData.favorites || favsData || [])
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [userEmail])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleSaveProfile = async (e) => {
    e.preventDefault()
    setSaving(true)
    setSaveSuccess(false)
    try {
      const resp = await fetch(`/api/user/profile?email=${encodeURIComponent(userEmail)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editForm),
      })
      if (!resp.ok) throw new Error('Kunde inte spara profil')
      const updated = await resp.json()
      setProfile(prev => ({ ...prev, ...updated }))
      setEditing(false)
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  if (!userEmail) {
    return (
      <div className="text-center py-20 fade-in">
        <p className="text-4xl mb-4">🔒</p>
        <h2 className="text-xl font-bold mb-2">Logga in</h2>
        <p className="text-sm mb-6" style={{ color: 'var(--color-text-muted)' }}>
          Du behöver vara inloggad för att se din profil.
        </p>
        {onBack && (
          <button onClick={onBack} className="btn btn-secondary">Tillbaka</button>
        )}
      </div>
    )
  }

  if (loading) {
    return (
      <div className="text-center py-20 fade-in">
        <div className="w-8 h-8 border-2 rounded-full animate-spin mx-auto mb-4"
          style={{ borderColor: 'var(--color-border)', borderTopColor: 'var(--color-brand)' }} />
        <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Laddar profil...</p>
      </div>
    )
  }

  if (error && !profile) {
    return (
      <div className="text-center py-20 fade-in">
        <p className="text-4xl mb-4">😔</p>
        <h2 className="text-lg font-bold mb-2">Något gick fel</h2>
        <p className="text-sm mb-4" style={{ color: 'var(--color-text-muted)' }}>{error}</p>
        <button onClick={fetchData} className="btn btn-primary">Försök igen</button>
      </div>
    )
  }

  const tier = TIER_BADGES[profile?.subscription_tier] || TIER_BADGES.free
  const limit = profile?.generation_limit || {}

  return (
    <section className="fade-in">
      {/* Back button */}
      {onBack && (
        <button onClick={onBack} className="text-sm mb-4" style={{ color: 'var(--color-text-muted)' }}>
          ← Tillbaka
        </button>
      )}

      {/* Profile header */}
      <div className="card p-5 mb-5 fade-up">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h1 className="text-xl font-bold tracking-tight">
                {profile?.name || userEmail.split('@')[0]}
              </h1>
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full"
                style={{ background: tier.bg, color: tier.color }}>
                {tier.label}
              </span>
            </div>
            <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>{userEmail}</p>
            {profile?.city && (
              <p className="text-sm mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>
                📍 {profile.city}
              </p>
            )}
            {profile?.bio && (
              <p className="text-sm mt-2" style={{ color: 'var(--color-text-secondary)' }}>
                {profile.bio}
              </p>
            )}
          </div>
          {!editing && (
            <button onClick={() => setEditing(true)}
              className="btn-pill text-xs shrink-0">
              Redigera
            </button>
          )}
        </div>

        {saveSuccess && (
          <div className="text-xs font-medium mt-3 fade-in" style={{ color: 'var(--color-brand)' }}>
            Profil sparad!
          </div>
        )}
      </div>

      {/* Edit form */}
      {editing && (
        <div className="card p-5 mb-5 fade-up">
          <h2 className="font-bold text-base mb-4">Redigera profil</h2>
          <form onSubmit={handleSaveProfile} className="space-y-3">
            <div>
              <label className="text-xs font-medium block mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Namn
              </label>
              <input
                type="text"
                value={editForm.name}
                onChange={e => setEditForm(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Ditt namn"
                className="w-full px-4 py-2.5 text-sm border rounded-lg outline-none focus:ring-2 focus:ring-green-700"
                style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg)' }}
              />
            </div>
            <div>
              <label className="text-xs font-medium block mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Stad
              </label>
              <input
                type="text"
                value={editForm.city}
                onChange={e => setEditForm(prev => ({ ...prev, city: e.target.value }))}
                placeholder="T.ex. Örebro"
                className="w-full px-4 py-2.5 text-sm border rounded-lg outline-none focus:ring-2 focus:ring-green-700"
                style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg)' }}
              />
            </div>
            <div>
              <label className="text-xs font-medium block mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Bio
              </label>
              <textarea
                value={editForm.bio}
                onChange={e => setEditForm(prev => ({ ...prev, bio: e.target.value }))}
                placeholder="Berätta lite om dig..."
                rows={3}
                className="w-full px-4 py-2.5 text-sm border rounded-lg outline-none focus:ring-2 focus:ring-green-700 resize-none"
                style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg)' }}
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_public"
                checked={editForm.is_public}
                onChange={e => setEditForm(prev => ({ ...prev, is_public: e.target.checked }))}
                className="rounded"
              />
              <label htmlFor="is_public" className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                Visa min profil publikt i communityn
              </label>
            </div>
            <div className="flex gap-2 pt-2">
              <button type="submit" disabled={saving} className="btn btn-primary text-sm px-5 py-2">
                {saving ? 'Sparar...' : 'Spara'}
              </button>
              <button type="button" onClick={() => setEditing(false)} className="btn btn-secondary text-sm px-5 py-2">
                Avbryt
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Generation limit */}
      {limit.total > 0 && (
        <div className="card px-4 py-3 mb-5 fade-up delay-1" style={{ background: 'var(--color-brand-light)' }}>
          <div className="flex items-center justify-between">
            <div>
              <span className="text-sm font-medium" style={{ color: 'var(--color-brand-dark)' }}>
                Menyer idag
              </span>
              <span className="text-sm ml-2" style={{ color: 'var(--color-brand)' }}>
                {limit.remaining} av {limit.total} kvar
              </span>
            </div>
            {limit.remaining === 0 && (
              <span className="text-xs font-semibold" style={{ color: 'var(--color-accent)' }}>
                Gränsen nådd
              </span>
            )}
          </div>
          <div className="w-full rounded-full h-1.5 mt-2" style={{ background: 'rgba(0,0,0,0.1)' }}>
            <div className="h-1.5 rounded-full transition-all" style={{
              width: `${Math.min(100, ((limit.total - limit.remaining) / limit.total) * 100)}%`,
              background: limit.remaining > 0 ? 'var(--color-brand-dark)' : 'var(--color-accent)',
            }} />
          </div>
        </div>
      )}

      {/* Upgrade CTA */}
      {(!profile?.subscription_tier || profile.subscription_tier === 'free') && (
        <div className="card p-5 mb-5 text-center fade-up delay-2"
          style={{ background: 'var(--color-accent-light)', borderColor: 'var(--color-accent)' }}>
          <p className="font-bold text-base mb-1">Lås upp mer med Premium</p>
          <p className="text-sm mb-4" style={{ color: 'var(--color-text-secondary)' }}>
            Obegränsade menyer, favoritrecept och mer.
          </p>
          <button className="btn btn-primary text-sm px-6 py-2.5">Uppgradera</button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 mb-4">
        {[['history', 'Menyhistorik'], ['favorites', 'Favoriter']].map(([value, label]) => (
          <button
            key={value}
            onClick={() => setTab(value)}
            className={`btn-pill ${tab === value ? 'active' : ''}`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Menu history */}
      {tab === 'history' && (
        <div className="fade-in">
          {menus.length > 0 ? (
            <div className="space-y-2">
              {menus.slice(0, 20).map((menu, i) => (
                <div key={menu.id || i} className="card p-4 flex items-center justify-between">
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">
                      {menu.title || `Vecka ${menu.week_number}`}
                    </p>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
                      {menu.created_at
                        ? new Date(menu.created_at).toLocaleDateString('sv-SE')
                        : menu.date_range || ''}
                      {menu.num_meals && ` — ${menu.num_meals} middagar`}
                    </p>
                  </div>
                  <div className="text-right shrink-0 ml-3">
                    <span className="font-bold" style={{ color: 'var(--color-accent)' }}>
                      {Math.round(menu.total_cost)} kr
                    </span>
                    {menu.total_savings > 0 && (
                      <span className="block text-xs font-medium" style={{ color: 'var(--color-brand)' }}>
                        −{Math.round(menu.total_savings)} kr
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <p className="text-3xl mb-3">📋</p>
              <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                Du har inte skapat några menyer ännu.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Favorites */}
      {tab === 'favorites' && (
        <div className="fade-in">
          {favorites.length > 0 ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {favorites.map((recipe, i) => (
                <div key={recipe.id || i} className="card p-4">
                  <div className="flex items-start gap-3">
                    {recipe.image_url && (
                      <img src={recipe.image_url} alt={recipe.title}
                        className="w-14 h-14 rounded-lg object-cover shrink-0" loading="lazy" />
                    )}
                    <div className="min-w-0">
                      <p className="text-sm font-medium leading-snug">{recipe.title}</p>
                      <div className="flex items-center gap-2 mt-1 text-xs" style={{ color: 'var(--color-text-muted)' }}>
                        {recipe.cook_time_minutes && <span>{recipe.cook_time_minutes} min</span>}
                        {recipe.difficulty && <span>{recipe.difficulty}</span>}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <p className="text-3xl mb-3">⭐</p>
              <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                Inga favoritrecept ännu. Gilla recept i din veckomeny för att spara dem här.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Error banner */}
      {error && profile && (
        <div className="card p-4 mt-5 fade-in" style={{ background: '#fff5f5', borderColor: '#ffc9c9' }}>
          <p className="text-sm" style={{ color: '#c92a2a' }}>{error}</p>
        </div>
      )}
    </section>
  )
}
