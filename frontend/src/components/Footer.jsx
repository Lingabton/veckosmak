export default function Footer() {
  return (
    <footer className="border-t border-gray-200 mt-auto print:hidden">
      <div className="max-w-3xl mx-auto px-4 py-5 flex flex-wrap items-center justify-between gap-2 text-xs text-gray-400">
        <div className="flex items-center gap-2">
          <img src="/logo.svg" alt="" className="w-5 h-5 opacity-40" />
          <span><strong className="text-gray-500">Veckosmak</strong> — Gratis menyplanering med veckans erbjudanden</span>
        </div>
        <div className="flex gap-4">
          <span>📍 ICA Maxi Örebro</span>
          <span>600+ recept</span>
          <span>{new Date().getFullYear()}</span>
        </div>
      </div>
    </footer>
  )
}
