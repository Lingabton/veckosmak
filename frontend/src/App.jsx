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
  } = useMenu()

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-green-700 text-white py-5 px-4 shadow-sm print:hidden">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div>
            <a href="/" className="text-2xl font-bold hover:text-green-100 transition-colors"
              onClick={(e) => { e.preventDefault(); setView(menu ? 'menu' : 'preferences') }}
              aria-label="Veckosmak — startsida">
              Veckosmak
            </a>
            <p className="text-green-200 text-sm mt-0.5">Smartare middagar med veckans erbjudanden</p>
          </div>
          {menu && (
            <nav aria-label="Huvudnavigation" className="flex gap-3 text-sm">
              <button onClick={() => setView('menu')}
                className={`px-3 py-1 rounded-full transition-colors ${view === 'menu' ? 'bg-green-600 text-white' : 'text-green-200 hover:text-white'}`}
                aria-current={view === 'menu' ? 'page' : undefined}>Meny</button>
              <button onClick={() => setView('shopping')}
                className={`px-3 py-1 rounded-full transition-colors ${view === 'shopping' ? 'bg-green-600 text-white' : 'text-green-200 hover:text-white'}`}
                aria-current={view === 'shopping' ? 'page' : undefined}>Inköpslista</button>
            </nav>
          )}
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6 flex-1 w-full">
        {error && (
          <div role="alert" className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 mb-4 text-sm">
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
              loading={loading}
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
            /* Empty state (#7) */
            <div className="text-center py-16">
              <h2 className="text-lg font-semibold text-gray-900 mb-2">Ingen meny ännu</h2>
              <p className="text-gray-500 text-sm mb-4">Skapa en veckomeny för att komma igång.</p>
              <button onClick={() => setView('preferences')}
                className="px-6 py-2 bg-green-700 text-white rounded-lg hover:bg-green-800 transition-colors">
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
