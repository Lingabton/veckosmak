export default function Footer() {
  return (
    <footer className="bg-gray-100 border-t border-gray-200 mt-auto print:hidden">
      <div className="max-w-3xl mx-auto px-4 py-6">
        <p className="text-sm text-gray-600 leading-relaxed mb-4">
          <strong>Veckosmak</strong> är en gratis menyplaneringstjänst som matchar recept mot din butiks
          erbjudanden. Få recept, inköpslista och se hur mycket du sparar — varje vecka.
        </p>
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-gray-400">
          <span>ICA Maxi Boglundsängen, Örebro</span>
          <span>600+ recept med crowd-betyg</span>
          <span>Veckosmak {new Date().getFullYear()}</span>
        </div>
      </div>
    </footer>
  )
}
