export default function LoadingSkeleton() {
  return (
    <div className="space-y-4" role="status" aria-label="Skapar veckomeny">
      <div className="text-center py-10">
        <div className="text-5xl mb-4 animate-bounce">🍳</div>
        <p className="text-gray-700 font-semibold text-lg">Skapar din veckomeny...</p>
        <p className="text-gray-400 text-sm mt-1">Matchar erbjudanden mot recept (3–10 sek)</p>
      </div>
      <div className="animate-pulse space-y-4">
        <div className="bg-green-50 rounded-xl h-16" />
        <div className="grid gap-4 sm:grid-cols-2">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="bg-gray-100 rounded-xl h-56" />
          ))}
        </div>
      </div>
    </div>
  )
}
