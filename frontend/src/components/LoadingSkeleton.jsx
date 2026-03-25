export default function LoadingSkeleton() {
  return (
    <div className="space-y-4" role="status" aria-label="Skapar veckomeny">
      <div className="text-center py-8">
        <div className="inline-block w-8 h-8 border-4 border-green-200 border-t-green-700 rounded-full animate-spin" />
        <p className="text-gray-600 mt-4 font-medium">Skapar din veckomeny...</p>
        <p className="text-gray-400 text-sm mt-1">AI:n analyserar erbjudanden och väljer recept (3–10 sek)</p>
      </div>
      <div className="animate-pulse space-y-4">
        <div className="bg-green-50 rounded-xl h-20" />
        <div className="grid gap-4 sm:grid-cols-2">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="bg-gray-100 rounded-xl h-52" />
          ))}
        </div>
      </div>
    </div>
  )
}
