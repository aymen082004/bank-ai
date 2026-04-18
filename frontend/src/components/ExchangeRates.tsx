import { Calculator } from 'lucide-react';

const currencies = [
  { flag: '🇨🇦', code: 'CAD', qty: '1', buy: 2.082, sell: 2.136 },
  { flag: '🇨🇭', code: 'CHF', qty: '10', buy: 36.281, sell: 37.446 },
  { flag: '🇨🇳', code: 'CNY', qty: '1', buy: 0.410, sell: 0.437 },
  { flag: '🇪🇺', code: 'EUR', qty: '1', buy: 3.372, sell: 3.449 },
  { flag: '🇬🇧', code: 'GBP', qty: '1', buy: 3.853, sell: 3.957 },
  { flag: '🇯🇵', code: 'JPY', qty: '1000', buy: 17.858, sell: 18.495 },
  { flag: '🇰🇼', code: 'KWD', qty: '1', buy: 9.882, sell: 10.005 },
  { flag: '🇸🇦', code: 'SAR', qty: '1', buy: 0.810, sell: 0.821 },
  { flag: '🇺🇸', code: 'USD', qty: '1', buy: 3.041, sell: 3.079 },
  { flag: '🇦🇪', code: 'AED', qty: '1', buy: 0.828, sell: 0.838 },
];

const today = new Date().toLocaleDateString('fr-FR', {
  weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
});

export default function ExchangeRates() {
  return (
    <section className="py-16" style={{ background: 'linear-gradient(135deg, #dce8f5 0%, #e8eef6 50%, #dce4f0 100%)' }}>
      <div className="max-w-screen-xl mx-auto px-6">
        {/* Title */}
        <div className="text-center mb-8">
          <h2 className="text-3xl font-black text-[#1c2951] mb-3">
            Vos outils financiers en un clic
          </h2>
          <p className="text-gray-600 text-sm max-w-2xl mx-auto leading-relaxed">
            Utilisez notre simulateur de crédit pour estimer vos mensualités et découvrez notre<br />
            convertisseur de change pour suivre les fluctuations des devises.
          </p>
        </div>

        {/* Two pill CTA buttons */}
        <div className="flex flex-col sm:flex-row justify-center gap-4 mb-10">
          <a
            href="#"
            className="flex items-center justify-center gap-3 bg-[#1c2951] text-white px-10 py-4 rounded-full font-semibold hover:bg-[#263766] transition-colors text-sm"
          >
            <Calculator size={18} />
            Simulateur de crédit
          </a>
          <a
            href="#"
            className="flex items-center justify-center gap-3 bg-[#c8102e] text-white px-10 py-4 rounded-full font-semibold hover:bg-red-700 transition-colors text-sm"
          >
            {/* Currency icon */}
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 6v6l4 2" />
            </svg>
            Convertisseur de change
          </a>
        </div>

        {/* Date */}
        <p className="text-center text-gray-500 text-sm italic mb-6">
          Cours de change des principales devises<br />
          <span className="capitalize">{today}</span>
        </p>

        {/* Horizontal scrollable currency cards */}
        <div className="overflow-x-auto -mx-2 px-2 pb-2">
          <div className="flex gap-3" style={{ minWidth: 'max-content' }}>
            {currencies.map((cur) => (
              <div
                key={cur.code}
                className="group bg-white rounded-xl p-4 flex flex-col items-center shadow-sm border border-white/80 hover:shadow-xl hover:-translate-y-2 transition-all duration-300 cursor-pointer"
                style={{ minWidth: '120px' }}
              >
                <span className="text-3xl mb-2 group-hover:scale-110 transition-transform duration-300">{cur.flag}</span>
                <div className="text-[#1c2951] font-bold text-sm mb-3 group-hover:text-[#c8102e] transition-colors duration-300">
                  {cur.qty} {cur.code}
                </div>
                <div className="w-full space-y-1">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-gray-500">Achat :</span>
                    <span className="text-emerald-600 font-semibold">{cur.buy.toFixed(cur.buy < 1 ? 3 : cur.buy > 10 ? 3 : 3)}</span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-gray-500">Vente :</span>
                    <span className="text-[#c8102e] font-semibold">{cur.sell.toFixed(3)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
