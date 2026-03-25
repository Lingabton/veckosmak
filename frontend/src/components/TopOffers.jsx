export default function TopOffers({ offers, preferences, setPreferences, onGenerate, onBack, loading, loadingOffers }) {
  const pinned = new Set(preferences.pinned_offer_ids || [])

  const togglePin = (offerId) => {
    const next = new Set(pinned)
    if (next.has(offerId)) next.delete(offerId)
    else next.add(offerId)
    setPreferences({ ...preferences, pinned_offer_ids: [...next] })
  }

  if (loadingOffers) {
    return (
      <div className="text-center py-12">
        <div className="inline-block w-6 h-6 border-3 border-green-200 border-t-green-700 rounded-full animate-spin" />
        <p className="text-gray-500 text-sm mt-3">Hämtar veckans bästa erbjudanden...</p>
      </div>
    )
  }

  // Sort by discount descending
  const sortedOffers = [...offers].sort((a, b) => {
    const da = a.original_price ? (1 - a.offer_price / a.original_price) : 0
    const db = b.original_price ? (1 - b.offer_price / b.original_price) : 0
    return db - da
  })
  const bestDealId = sortedOffers[0]?.id

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <button onClick={onBack} className="text-sm text-gray-500 hover:text-green-700 transition-colors">
          ← Tillbaka
        </button>
        <button onClick={onGenerate} disabled={loading}
          className="text-sm font-medium text-green-700 hover:text-green-800 disabled:opacity-50">
          {loading ? 'Skapar...' : 'Hoppa över →'}
        </button>
      </div>

      <h1 className="text-xl font-bold text-gray-900 mb-1">Veckans bästa köp</h1>
      <p className="text-sm text-gray-600 mb-6">
        Välj erbjudanden att bygga menyn kring. Du behöver inte välja alla.
      </p>

      {offers.length === 0 ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-sm text-yellow-800 mb-6">
          Inga erbjudanden hittades just nu. Du kan fortfarande generera en meny.
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 mb-6">
          {sortedOffers.map(offer => {
            const isPinned = pinned.has(offer.id)
            const isBest = offer.id === bestDealId
            const discount = offer.original_price
              ? Math.round((1 - offer.offer_price / offer.original_price) * 100)
              : null
            return (
              <button key={offer.id} onClick={() => togglePin(offer.id)}
                className={`text-left p-3 rounded-xl border-2 transition-all relative ${
                  isPinned ? 'border-green-600 bg-green-50 shadow-sm' : 'border-gray-200 bg-white hover:border-green-300'
                }`}>
                {isBest && (
                  <span className="absolute -top-2 -right-2 bg-orange-500 text-white text-xs px-2 py-0.5 rounded-full font-medium shadow-sm">
                    Bästa deal
                  </span>
                )}
                <div className="flex items-start gap-3">
                  {offer.image_url && (
                    <img src={offer.image_url} alt="" className="w-14 h-14 rounded-lg object-cover shrink-0 bg-gray-100" loading="lazy" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 text-sm">{offer.product_name}</p>
                    {offer.brand && <p className="text-xs text-gray-500">{offer.brand}</p>}
                    <div className="flex items-baseline gap-2 mt-1">
                      <span className="font-bold text-green-700">{Math.round(offer.offer_price)} {offer.unit}</span>
                      {discount > 0 && <span className="text-xs text-green-600 font-medium">-{discount}%</span>}
                      {offer.original_price && (
                        <span className="text-xs text-gray-400 line-through">{Math.round(offer.original_price)}</span>
                      )}
                    </div>
                    {offer.quantity_deal && <p className="text-xs text-green-600 mt-0.5">{offer.quantity_deal}</p>}
                  </div>
                </div>
                {isPinned && (
                  <span className="inline-block mt-2 text-xs bg-green-700 text-white px-2 py-0.5 rounded-full">Vald</span>
                )}
              </button>
            )
          })}
        </div>
      )}

      <button onClick={onGenerate} disabled={loading}
        className="w-full py-3.5 px-4 bg-green-700 text-white font-semibold rounded-lg hover:bg-green-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-lg">
        {loading ? 'Skapar din veckomeny...' : (
          pinned.size > 0 ? `Skapa meny med ${pinned.size} bästa köp` : 'Skapa meny (överraska mig!)'
        )}
      </button>
      {pinned.size === 0 && (
        <p className="text-center text-xs text-gray-400 mt-2">Vi väljer de smartaste kombinationerna åt dig</p>
      )}
    </div>
  )
}
