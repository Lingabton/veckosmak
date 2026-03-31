import { useState, useEffect } from 'react'

const STEPS = [
  { text: 'Analyserar 198 erbjudanden...', icon: '🏷️' },
  { text: 'Matchar 1300+ recept mot dina preferenser...', icon: '🔍' },
  { text: 'AI skapar din perfekta vecka...', icon: '✨' },
  { text: 'Optimerar for basta pris...', icon: '💰' },
]

const FLOATING_EMOJIS = ['🥕', '🍋', '🧅', '🫒', '🌿', '🍅', '🥑', '🍳']

export default function LoadingSkeleton() {
  const [step, setStep] = useState(0)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const stepTimers = [
      setTimeout(() => setStep(1), 4000),
      setTimeout(() => setStep(2), 12000),
      setTimeout(() => setStep(3), 28000),
    ]
    return () => stepTimers.forEach(clearTimeout)
  }, [])

  // Smooth progress bar
  useEffect(() => {
    const targets = [22, 52, 82, 96]
    const target = targets[step] || 22
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= target) return prev
        const remaining = target - prev
        const increment = Math.max(0.15, remaining * 0.03)
        return Math.min(prev + increment, target)
      })
    }, 50)
    return () => clearInterval(interval)
  }, [step])

  return (
    <div className="fade-in" role="status" aria-live="polite">
      <div className="text-center py-16 relative">

        {/* Floating food emojis — very faint, decorative */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
          {FLOATING_EMOJIS.map((emoji, i) => (
            <span
              key={i}
              className="absolute text-2xl select-none"
              style={{
                left: `${10 + (i * 12) % 80}%`,
                top: `${15 + ((i * 37) % 60)}%`,
                opacity: 0.06,
                animation: `floatEmoji ${6 + (i % 3) * 2}s ease-in-out infinite`,
                animationDelay: `${i * 0.7}s`,
              }}
            >{emoji}</span>
          ))}
        </div>

        {/* Animated gradient orb */}
        <div className="relative w-24 h-24 mx-auto mb-8">
          <div className="absolute inset-0 rounded-full"
            style={{
              background: 'radial-gradient(circle at 40% 40%, var(--color-brand), rgba(26,92,53,0.3))',
              animation: 'orbFloat 4s ease-in-out infinite, orbPulse 3s ease-in-out infinite',
            }}
          />
          <div className="absolute inset-2 rounded-full"
            style={{
              background: 'radial-gradient(circle at 60% 60%, var(--color-accent), rgba(212,85,42,0.2))',
              animation: 'orbFloat 5s ease-in-out infinite reverse, orbPulse 3.5s ease-in-out infinite 0.5s',
            }}
          />
          <div className="absolute inset-4 rounded-full"
            style={{
              background: 'radial-gradient(circle at 50% 50%, rgba(255,255,255,0.9), rgba(255,255,255,0.1))',
              filter: 'blur(8px)',
            }}
          />
        </div>

        {/* Headline */}
        <h2 className="font-display text-[1.75rem] font-bold mb-3" style={{ letterSpacing: '-0.03em' }}>
          Skapar din veckomeny
        </h2>

        {/* Step text with stagger pulse */}
        <div className="h-6 flex items-center justify-center mb-8">
          <p className="text-sm flex items-center gap-2" style={{
            color: 'var(--color-text-muted)',
            animation: 'stepPulse 2s ease-in-out infinite',
          }}>
            <span className="text-base">{STEPS[step].icon}</span>
            <span>{STEPS[step].text}</span>
          </p>
        </div>

        {/* Progress bar — smooth fill */}
        <div className="max-w-xs mx-auto mb-6">
          <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--color-border-light)' }}>
            <div
              className="h-full rounded-full relative"
              style={{
                width: `${progress}%`,
                background: 'linear-gradient(90deg, var(--color-brand), var(--color-accent))',
                transition: 'width 0.3s ease-out',
                boxShadow: '0 0 12px var(--color-glow-brand)',
              }}
            >
              {/* Shimmer on progress bar */}
              <div className="absolute inset-0 rounded-full" style={{
                background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.4) 50%, transparent 100%)',
                backgroundSize: '200% 100%',
                animation: 'shimmer 1.5s ease-in-out infinite',
              }} />
            </div>
          </div>
        </div>

        {/* Step indicators */}
        <div className="flex justify-center gap-3">
          {STEPS.map((s, i) => (
            <div key={i} className="flex items-center gap-1.5 transition-all duration-500" style={{
              opacity: i <= step ? 1 : 0.3,
            }}>
              <div
                className="rounded-full transition-all duration-700"
                style={{
                  width: i === step ? 24 : i < step ? 8 : 6,
                  height: 6,
                  background: i <= step
                    ? (i === step ? 'linear-gradient(90deg, var(--color-brand), var(--color-accent))' : 'var(--color-brand)')
                    : 'var(--color-border)',
                  boxShadow: i === step ? '0 0 8px var(--color-glow-brand)' : 'none',
                }}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Inline keyframes for this component */}
      <style>{`
        @keyframes floatEmoji {
          0%, 100% { transform: translateY(0) rotate(0deg); }
          33% { transform: translateY(-12px) rotate(5deg); }
          66% { transform: translateY(-6px) rotate(-3deg); }
        }
        @keyframes stepPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.55; }
        }
      `}</style>
    </div>
  )
}
