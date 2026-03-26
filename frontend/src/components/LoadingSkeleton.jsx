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
        <div className="w-10 h-10 border-2 rounded-full animate-spin mx-auto mb-5"
          style={{borderColor:'var(--color-border)',borderTopColor:'var(--color-brand)'}} />
        <p className="text-xl font-bold mb-2">Skapar din veckomeny</p>
        <p className="text-sm" style={{color:'var(--color-text-muted)'}}>{STEPS[step]}</p>
        <div className="flex justify-center gap-1.5 mt-5">
          {STEPS.map((_,i) => <div key={i} className="w-2 h-2 rounded-full transition-all duration-300"
            style={{background:i<=step?'var(--color-brand)':'var(--color-border)'}} />)}
        </div>
      </div>
    </div>
  )
}
