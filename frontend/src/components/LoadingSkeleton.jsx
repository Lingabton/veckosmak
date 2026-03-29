import { useState, useEffect } from 'react'

const STEPS = ['Ansluter...','Hämtar erbjudanden...','Matchar recept...','Optimerar din meny...','Nästan klart...']

export default function LoadingSkeleton() {
  const [step, setStep] = useState(0)
  useEffect(() => {
    const t = [setTimeout(()=>setStep(1),3000),setTimeout(()=>setStep(2),8000),setTimeout(()=>setStep(3),15000),setTimeout(()=>setStep(4),25000)]
    return () => t.forEach(clearTimeout)
  }, [])

  return (
    <div className="fade-in" role="status">
      <div className="text-center py-20">
        {/* Animated rings */}
        <div className="relative w-16 h-16 mx-auto mb-6">
          <div className="absolute inset-0 border-2 rounded-full animate-spin"
            style={{borderColor:'transparent',borderTopColor:'var(--color-brand)', animationDuration:'1s'}} />
          <div className="absolute inset-2 border-2 rounded-full animate-spin"
            style={{borderColor:'transparent',borderBottomColor:'var(--color-accent)', animationDuration:'1.5s', animationDirection:'reverse'}} />
        </div>
        <p className="font-display text-2xl font-bold mb-2" style={{ letterSpacing: '-0.02em' }}>
          Skapar din veckomeny
        </p>
        <p className="text-sm" style={{color:'var(--color-text-muted)'}}>{STEPS[step]}</p>
        <div className="flex justify-center gap-2 mt-6">
          {STEPS.map((_,i) => (
            <div key={i} className="h-1.5 rounded-full transition-all duration-500"
              style={{
                width: i <= step ? 28 : 8,
                background: i <= step ? 'var(--color-brand)' : 'var(--color-border)',
              }} />
          ))}
        </div>
      </div>
    </div>
  )
}
