import { useState, useEffect } from 'react'
import { useMenu } from './hooks/useMenu'
import PreferencesForm from './components/PreferencesForm'
import TopOffers from './components/TopOffers'
import WeeklyMenu from './components/WeeklyMenu'
import ShoppingList from './components/ShoppingList'
import LoadingSkeleton from './components/LoadingSkeleton'
import ErrorBoundary from './components/ErrorBoundary'

function App() {
  const {
    preferences, setPreferences,
    menu, topOffers, loading, loadingOffers, swapping, error,
    view, setView,
    generateMenu, goToOffers, swapRecipe, sendFeedback,
    copySuccess, copyToClipboard,
    expandAll, setExpandAll,
    isReturning, bonusOffers,
    menuHistory, totalSavings,
  } = useMenu()

  return (
    <div className="min-h-screen flex flex-col" style={{ background: 'var(--color-bg)' }}>
      {/* ── Header ── full-bleed dark with grain */}
      <header className="no-print relative overflow-hidden" style={{ background: 'var(--color-brand-darker)' }}>
        {/* Grain texture overlay */}
        <div className="absolute inset-0 pointer-events-none" style={{
          opacity: 0.06,
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`,
          backgroundRepeat: 'repeat',
          backgroundSize: '256px 256px',
        }} />
        {/* Subtle bottom glow */}
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[600px] h-[1px]" style={{
          background: 'linear-gradient(90deg, transparent, rgba(232,245,233,0.15), transparent)',
        }} />

        <div className="max-w-2xl mx-auto px-5 py-3 flex items-center justify-between relative z-10">
          <a href="/" onClick={(e) => { e.preventDefault(); setView(menu ? 'menu' : 'preferences') }}
            className="flex items-center gap-2.5 text-white hover:opacity-90 transition-opacity group">
            <span className="text-xl opacity-60 group-hover:opacity-90 transition-opacity" style={{ filter: 'drop-shadow(0 0 6px rgba(232,245,233,0.3))' }}>&#10043;</span>
            <span className="font-display text-[1.65rem] font-bold tracking-tight" style={{ letterSpacing: '-0.04em' }}>veckosmak</span>
            {!menu && (
              <span className="text-[10px] font-light tracking-widest text-green-300/50 hidden sm:inline uppercase ml-1" style={{ letterSpacing: '0.14em' }}>
                erbjudande till middag
              </span>
            )}
          </a>
          <div className="flex items-center gap-1.5">
            {menu && (
              <nav className="flex gap-1 p-1 rounded-full" style={{ background: 'rgba(255,255,255,0.06)', backdropFilter: 'blur(12px)' }}>
                {[['preferences', 'Ny meny'], ['menu', 'Meny'], ['shopping', 'Lista']].map(([v, label]) => (
                  <button key={v} onClick={() => setView(v)}
                    className="relative px-4 py-1.5 rounded-full text-xs sm:text-sm font-medium transition-all"
                    style={{
                      background: view === v ? 'rgba(255,255,255,0.15)' : 'transparent',
                      color: view === v ? '#ffffff' : 'rgba(187,227,197,0.7)',
                      backdropFilter: view === v ? 'blur(8px)' : 'none',
                      boxShadow: view === v ? 'inset 0 1px 0 rgba(255,255,255,0.1), 0 1px 3px rgba(0,0,0,0.2)' : 'none',
                    }}
                  >{label}</button>
                ))}
              </nav>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-5 py-8 flex-1 w-full">
        {/* ── Error banner ── glass morphism red */}
        {error && (
          <div className="fade-in mb-6 p-4 rounded-2xl relative overflow-hidden" style={{
            background: 'rgba(255, 240, 240, 0.7)',
            backdropFilter: 'blur(16px) saturate(1.6)',
            WebkitBackdropFilter: 'blur(16px) saturate(1.6)',
            border: '1px solid rgba(201, 42, 42, 0.15)',
            boxShadow: '0 4px 20px rgba(201, 42, 42, 0.08), inset 0 1px 0 rgba(255,255,255,0.5)',
          }}>
            <p className="text-sm font-medium" style={{ color: '#a32222' }}>{error}</p>
            <button onClick={generateMenu} className="text-sm font-semibold mt-2 underline underline-offset-2 transition-opacity hover:opacity-70" style={{ color: '#a32222' }}>
              Forsok igen
            </button>
          </div>
        )}

        <ErrorBoundary>
          {loading ? <LoadingSkeleton />
           : view === 'preferences' ? (
            <PreferencesForm
              preferences={preferences} setPreferences={setPreferences}
              goToOffers={goToOffers} generateMenu={generateMenu}
              loading={loading} isReturning={isReturning}
              menu={menu} setView={setView}
              totalSavings={totalSavings} menuHistory={menuHistory}
            />
          ) : view === 'offers' ? (
            <TopOffers
              offers={topOffers} preferences={preferences} setPreferences={setPreferences}
              onGenerate={generateMenu} onBack={() => setView('preferences')}
              loading={loading} loadingOffers={loadingOffers}
            />
          ) : view === 'menu' && menu ? (
            <WeeklyMenu
              menu={menu} onSwap={swapRecipe} swapping={swapping}
              onShowShopping={() => setView('shopping')} onBack={() => setView('preferences')}
              onRegenerate={generateMenu} onFeedback={sendFeedback}
              expandAll={expandAll} setExpandAll={setExpandAll}
              bonusOffers={bonusOffers}
              preferences={preferences} setPreferences={setPreferences}
            />
          ) : view === 'shopping' && menu ? (
            <ShoppingList
              menu={menu} onBack={() => setView('menu')}
              copySuccess={copySuccess} onCopy={copyToClipboard}
            />
          ) : (
            <div className="text-center py-20 fade-in">
              <p className="text-5xl mb-4">&#127869;</p>
              <h2 className="text-xl font-bold mb-2">Ingen meny skapad</h2>
              <p className="text-sm mb-6" style={{ color: 'var(--color-text-muted)' }}>Skapa en veckomeny for att komma igang.</p>
              <button onClick={() => setView('preferences')} className="btn btn-primary">Skapa veckomeny</button>
            </div>
          )}
        </ErrorBoundary>
      </main>

      {/* ── Footer ── editorial, refined */}
      <footer className="no-print relative">
        {/* Top gradient line */}
        <div className="h-[1px] w-full" style={{
          background: 'linear-gradient(90deg, transparent 5%, var(--color-border) 30%, var(--color-brand-light) 50%, var(--color-border) 70%, transparent 95%)',
        }} />
        <div className="max-w-2xl mx-auto px-5 py-5 flex flex-wrap items-center justify-between gap-3 text-xs" style={{ color: 'var(--color-text-muted)' }}>
          <span className="flex items-center gap-2">
            <span className="font-display text-sm font-semibold" style={{ color: 'var(--color-text-secondary)', letterSpacing: '-0.02em' }}>veckosmak</span>
            <span className="opacity-30">&middot;</span>
            <span>gratis menyplanering</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span>ICA</span>
            <span className="opacity-30">&middot;</span>
            <span>Willys</span>
            <span className="opacity-30">&middot;</span>
            <span>1300+ recept</span>
            <span className="opacity-30">&middot;</span>
            <span>{new Date().getFullYear()}</span>
          </span>
        </div>
      </footer>
    </div>
  )
}

export default App
