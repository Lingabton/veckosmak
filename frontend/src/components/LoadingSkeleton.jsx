import { useState, useEffect } from 'react'

const STEPS = [
  'Ansluter till servern...',
  'Hämtar veckans erbjudanden...',
  'Matchar mot recept...',
  'Optimerar din meny...',
  'Nästan klart...',
]

export default function LoadingSkeleton() {
  const [step, setStep] = useState(0)

  useEffect(() => {
    const timers = [
      setTimeout(() => setStep(1), 3000),
      setTimeout(() => setStep(2), 8000),
      setTimeout(() => setStep(3), 15000),
      setTimeout(() => setStep(4), 25000),
    ]
    return () => timers.forEach(clearTimeout)
  }, [])

  return (
    <div className="animate-fade-in" role="status">
      <div className="text-center py-16">
        <div className="w-8 h-8 border-2 rounded-full animate-spin mx-auto mb-5"
          style={{ borderColor: 'var(--border)', borderTopColor: 'var(--green)' }} />
        <p className="font-semibold text-lg mb-2">Skapar din veckomeny</p>
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>{STEPS[step]}</p>

        {/* Progress dots */}
        <div className="flex justify-center gap-1.5 mt-4">
          {STEPS.map((_, i) => (
            <div key={i} className="w-2 h-2 rounded-full transition-all duration-300"
              style={{ backgroundColor: i <= step ? 'var(--green)' : 'var(--border)' }} />
          ))}
        </div>
      </div>
      <div className="animate-pulse space-y-4">
        <div className="rounded-xl h-14" style={{ backgroundColor: 'var(--green-soft)' }} />
        <div className="grid gap-4 sm:grid-cols-2">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="rounded-2xl h-64" style={{ backgroundColor: 'var(--border-light)' }} />
          ))}
        </div>
      </div>
    </div>
  )
}
