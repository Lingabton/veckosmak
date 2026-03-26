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
      <header className="no-print" style={{ background: 'var(--color-brand-dark)' }}>
        <div className="max-w-2xl mx-auto px-5 py-4 flex items-center justify-between">
          <a href="/" onClick={(e) => { e.preventDefault(); setView(menu ? 'menu' : 'preferences') }}
            className="flex items-baseline gap-2 text-white hover:opacity-90 transition-opacity">
            <span className="text-xl font-bold tracking-tight">veckosmak</span>
            <span className="text-sm text-green-300 hidden sm:inline">från erbjudande till middag</span>
          </a>
          {menu && (
            <nav className="flex gap-1">
              {[['menu', 'Meny'], ['shopping', 'Inköpslista']].map(([v, label]) => (
                <button key={v} onClick={() => setView(v)}
                  className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all ${
                    view === v ? 'bg-white/20 text-white' : 'text-green-200 hover:text-white'
                  }`}>{label}</button>
              ))}
            </nav>
          )}
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-5 py-8 flex-1 w-full">
        {error && view !== 'preferences' && (
          <div className="card p-4 mb-6 fade-in" style={{ background: '#fff5f5', borderColor: '#ffc9c9' }}>
            <p className="text-sm" style={{ color: '#c92a2a' }}>{error}</p>
            <button onClick={generateMenu} className="text-sm font-medium mt-2 underline" style={{ color: '#c92a2a' }}>Försök igen</button>
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
            />
          ) : view === 'shopping' && menu ? (
            <ShoppingList
              menu={menu} onBack={() => setView('menu')}
              copySuccess={copySuccess} onCopy={copyToClipboard}
            />
          ) : (
            <div className="text-center py-20 fade-in">
              <p className="text-5xl mb-4">🍽</p>
              <h2 className="text-xl font-bold mb-2">Ingen meny skapad</h2>
              <p className="text-sm mb-6" style={{ color: 'var(--color-text-muted)' }}>Skapa en veckomeny för att komma igång.</p>
              <button onClick={() => setView('preferences')} className="btn btn-primary">Skapa veckomeny</button>
            </div>
          )}
        </ErrorBoundary>
      </main>

      <footer className="no-print" style={{ borderTop: '1px solid var(--color-border-light)' }}>
        <div className="max-w-2xl mx-auto px-5 py-4 flex flex-wrap items-center justify-between gap-2 text-xs" style={{ color: 'var(--color-text-muted)' }}>
          <span><b style={{ color: 'var(--color-text-secondary)' }}>veckosmak</b> — gratis menyplanering</span>
          <span>1100+ ICA-butiker · 600+ recept · {new Date().getFullYear()}</span>
        </div>
      </footer>
    </div>
  )
}

export default App
