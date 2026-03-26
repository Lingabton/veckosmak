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
  } = useMenu()

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: 'var(--bg)' }}>
      {/* Header */}
      <header className="print:hidden" style={{ backgroundColor: 'var(--green-deep)' }}>
        <div className="max-w-2xl mx-auto px-5 py-4 flex items-center justify-between">
          <a href="/" className="group" onClick={(e) => { e.preventDefault(); setView(menu ? 'menu' : 'preferences') }}>
            <span className="text-white text-xl font-bold tracking-tight">veckosmak</span>
            <span className="text-green-300 text-xs block mt-0.5 group-hover:text-green-200 transition-colors">smartare middagar</span>
          </a>
          {menu && (
            <nav className="flex gap-1 text-sm">
              {[['menu', 'Meny'], ['shopping', 'Inköpslista']].map(([v, label]) => (
                <button key={v} onClick={() => setView(v)}
                  className={`px-3.5 py-1.5 rounded-full transition-colors ${
                    view === v ? 'bg-white/20 text-white' : 'text-green-200 hover:text-white'
                  }`}>{label}</button>
              ))}
            </nav>
          )}
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-5 py-8 flex-1 w-full">
        {error && view !== 'preferences' && (
          <div role="alert" className="border rounded-lg p-4 mb-5 text-sm animate-fade-in"
            style={{ backgroundColor: '#fef2f2', borderColor: '#fecaca', color: '#b91c1c' }}>
            <p>{error}</p>
            <button onClick={generateMenu}
              className="mt-2 text-sm font-medium underline" style={{ color: '#b91c1c' }}>
              Försök igen
            </button>
          </div>
        )}

        <ErrorBoundary>
          {loading ? (
            <LoadingSkeleton />
          ) : view === 'preferences' ? (
            <PreferencesForm
              preferences={preferences} setPreferences={setPreferences}
              onGenerate={goToOffers} onGenerateDirect={generateMenu}
              loading={loading} isReturning={isReturning}
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
            <ShoppingList menu={menu} onBack={() => setView('menu')}
              copySuccess={copySuccess} onCopy={copyToClipboard} />
          ) : (
            <div className="text-center py-20 animate-fade-in">
              <h2 className="text-xl font-semibold mb-2">Ingen meny skapad</h2>
              <p className="text-gray-500 text-sm mb-6">Kom igång genom att skapa din veckomeny.</p>
              <button onClick={() => setView('preferences')}
                className="px-8 py-3 rounded-lg text-white font-medium transition-colors"
                style={{ backgroundColor: 'var(--accent)' }}>
                Skapa veckomeny
              </button>
            </div>
          )}
        </ErrorBoundary>
      </main>

      {/* Footer */}
      <footer className="print:hidden" style={{ borderTop: '1px solid var(--border)' }}>
        <div className="max-w-2xl mx-auto px-5 py-4 flex flex-wrap items-center justify-between gap-2 text-xs" style={{ color: 'var(--text-muted)' }}>
          <span><strong style={{ color: 'var(--text-secondary)' }}>veckosmak</strong> — gratis menyplanering</span>
          <span>ICA Maxi Boglundsängen, Örebro</span>
        </div>
      </footer>
    </div>
  )
}

export default App
