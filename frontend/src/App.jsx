import { useMenu } from './hooks/useMenu'
import PreferencesForm from './components/PreferencesForm'
import TopOffers from './components/TopOffers'
import WeeklyMenu from './components/WeeklyMenu'
import ShoppingList from './components/ShoppingList'
import LoadingSkeleton from './components/LoadingSkeleton'
import Footer from './components/Footer'
import ErrorBoundary from './components/ErrorBoundary'

function App() {
  const {
    preferences, setPreferences,
    menu, topOffers, loading, loadingOffers, swapping, error,
    view, setView,
    generateMenu, goToOffers, swapRecipe, sendFeedback,
    copySuccess, copyToClipboard,
    expandAll, setExpandAll,
    isReturning,
  } = useMenu()

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-green-700 text-white py-4 px-4 shadow-sm print:hidden">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <a href="/" className="flex items-center gap-2.5 hover:opacity-90 transition-opacity"
            onClick={(e) => { e.preventDefault(); setView(menu ? 'menu' : 'preferences') }}>
            <img src="/logo.svg" alt="" className="w-8 h-8" />
            <div>
              <span className="text-xl font-bold block leading-tight">Veckosmak</span>
              <span className="text-green-300 text-xs">Smartare middagar</span>
            </div>
          </a>
          {menu && (
            <nav className="flex gap-2 text-sm">
              <button onClick={() => setView('menu')}
                className={`px-3 py-1.5 rounded-full transition-colors ${view === 'menu' ? 'bg-green-600' : 'text-green-200 hover:text-white'}`}>
                Meny
              </button>
              <button onClick={() => setView('shopping')}
                className={`px-3 py-1.5 rounded-full transition-colors ${view === 'shopping' ? 'bg-green-600' : 'text-green-200 hover:text-white'}`}>
                Inköpslista
              </button>
            </nav>
          )}
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6 flex-1 w-full">
        {error && (
          <div role="alert" className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 mb-4 text-sm animate-fade-in">
            {error}
          </div>
        )}

        <ErrorBoundary>
          {loading ? (
            <LoadingSkeleton />
          ) : view === 'preferences' ? (
            <PreferencesForm
              preferences={preferences}
              setPreferences={setPreferences}
              onGenerate={goToOffers}
              onGenerateDirect={generateMenu}
              loading={loading}
              isReturning={isReturning}
            />
          ) : view === 'offers' ? (
            <TopOffers
              offers={topOffers}
              preferences={preferences}
              setPreferences={setPreferences}
              onGenerate={generateMenu}
              onBack={() => setView('preferences')}
              loading={loading}
              loadingOffers={loadingOffers}
            />
          ) : view === 'menu' && menu ? (
            <WeeklyMenu
              menu={menu}
              onSwap={swapRecipe}
              swapping={swapping}
              onShowShopping={() => setView('shopping')}
              onBack={() => setView('preferences')}
              onRegenerate={generateMenu}
              onFeedback={sendFeedback}
              expandAll={expandAll}
              setExpandAll={setExpandAll}
            />
          ) : view === 'shopping' && menu ? (
            <ShoppingList
              menu={menu}
              onBack={() => setView('menu')}
              copySuccess={copySuccess}
              onCopy={copyToClipboard}
            />
          ) : (
            <div className="text-center py-16 animate-fade-in">
              <div className="text-5xl mb-4">🍽️</div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">Ingen meny ännu</h2>
              <p className="text-gray-500 text-sm mb-4">Skapa en veckomeny för att komma igång.</p>
              <button onClick={() => setView('preferences')}
                className="px-6 py-2.5 btn-accent rounded-xl">
                Skapa veckomeny
              </button>
            </div>
          )}
        </ErrorBoundary>
      </main>

      <Footer />
    </div>
  )
}

export default App
