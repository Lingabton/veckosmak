export default function LoadingSkeleton() {
  return (
    <div className="animate-fade-in" role="status">
      <div className="text-center py-16">
        <div className="w-8 h-8 border-2 rounded-full animate-spin mx-auto mb-4"
          style={{ borderColor: 'var(--border)', borderTopColor: 'var(--green)' }} />
        <p className="font-semibold text-lg">Skapar din veckomeny</p>
        <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
          Matchar erbjudanden mot recept...
        </p>
      </div>
      <div className="animate-pulse space-y-4">
        <div className="rounded-xl h-14" style={{ backgroundColor: 'var(--green-soft)' }} />
        <div className="grid gap-4 sm:grid-cols-2">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="rounded-2xl h-64" style={{ backgroundColor: 'var(--border-light)' }} />
          ))}
        </div>
      </div>
    </div>
  )
}
