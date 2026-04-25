import { User, Grid, CreditCard } from 'lucide-react';

const features = [
  { icon: User, label: 'Consultez la situation de vos comptes en temps réel' },
  { icon: Grid, label: 'Gérez facilement vos virements' },
  { icon: CreditCard, label: 'Téléchargez et éditez vos relevés bancaires' },
];

const digitalProducts = [
  {
    name: 'BHnet',
    logo: 'BH\nnet',
    color: '#c8102e',
    bg: 'white',
    border: true,
  },
  {
    name: 'BH MPAY',
    logo: 'BH\nMPAY',
    color: '#c8102e',
    bg: 'white',
    border: true,
  },
  {
    name: 'E-TRADE',
    logo: 'E-TRADE',
    color: '#1c2951',
    bg: 'white',
    border: true,
  },
];

export default function DigitalBanking() {
  return (
    <>
      {/* ── Section 1: BH Net CTA ── */}
      <section className="py-14" style={{ background: '#f0f4f8' }}>
        <div className="max-w-screen-xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div>
            <p className="text-gray-500 text-sm mb-2">Gérez vos finances en toute simplicité et sécurité.</p>
            <h2 className="text-2xl md:text-3xl font-black text-[#1c2951] leading-tight">
              Découvrez BH Net : Votre<br />banque à portée de main
            </h2>
          </div>
          <div className="flex flex-col sm:flex-row gap-3 shrink-0">
            <a
              href="#"
              className="bg-[#c8102e] text-white px-8 py-3 rounded-full font-semibold text-sm hover:bg-red-700 transition-colors text-center whitespace-nowrap"
            >
              Crédit en ligne
            </a>
            <a
              href="#"
              className="bg-[#1c2951] text-white px-8 py-3 rounded-full font-semibold text-sm hover:bg-[#263766] transition-colors text-center whitespace-nowrap"
            >
              Assistance et réclamation
            </a>
          </div>
        </div>
      </section>

      {/* ── Section 2: App details ── */}
      <section className="py-14 bg-white overflow-hidden">
        <div className="max-w-screen-xl mx-auto px-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            {/* Left */}
            <div>
              <h3 className="text-xl font-black text-[#1c2951] mb-1">
                Application <span className="text-[#c8102e]">BH</span>net
              </h3>
              <p className="text-gray-600 text-sm leading-relaxed mb-6">
                Avec BH Net, gérez vos comptes bancaires, suivez vos investissements E-trade,
                et effectuez vos transactions en toute sécurité.
              </p>

              {/* Store badges */}
              <div className="flex gap-3 mb-8">
                <a
                  href="#"
                  className="flex items-center gap-2 bg-black text-white px-4 py-2.5 rounded-xl hover:bg-gray-900 transition-colors"
                >
                  {/* Google Play icon placeholder */}
                  <svg viewBox="0 0 24 24" className="w-6 h-6 fill-current">
                    <path d="M3.18 23.76c.3.16.65.18.97.06l11.65-11.65L12 9.37 3.18 23.76zm15.7-12.7L16.1 9.57 3.72.63C3.38.42 2.98.47 2.7.74L15.37 13.4l3.51-2.34zM20.4 10.7l-2.47-1.43-2.6 2.6 2.6 2.6 2.47-1.43c.7-.4.7-1.94 0-2.34zM3.18.24L15.37 12.43 12 9.06.24 23.76c.3.16.65.18.97.06L13.88 12.1.24.24z" />
                  </svg>
                  <div>
                    <div className="text-[9px] leading-none opacity-70">DISPONIBLE SUR</div>
                    <div className="text-sm font-semibold leading-none">Google Play</div>
                  </div>
                </a>
                <a
                  href="#"
                  className="flex items-center gap-2 bg-black text-white px-4 py-2.5 rounded-xl hover:bg-gray-900 transition-colors"
                >
                  <svg viewBox="0 0 814 1000" className="w-6 h-6 fill-current">
                    <path d="M788.1 340.9c-5.8 4.5-108.2 62.2-108.2 190.5 0 148.4 130.3 200.9 134.2 202.2-.6 3.2-20.7 71.9-68.7 141.9-42.8 61.6-87.5 123.1-155.5 123.1s-85.5-39.5-164-39.5c-76 0-103.7 40.8-165.9 40.8s-105-42.8-169.5-123.1C18.7 696.1 0 577.8 0 464c0-149.7 97.6-228.8 193.3-228.8 63.7 0 116.5 42.8 156 42.8 37.7 0 99.9-45 171.1-45 27.5 0 108.2 2.6 168.3 74.3z"/>
                  </svg>
                  <div>
                    <div className="text-[9px] leading-none opacity-70">Télécharger sur l'</div>
                    <div className="text-sm font-semibold leading-none">App Store</div>
                  </div>
                </a>
              </div>

              {/* Feature cards */}
              <div className="grid grid-cols-3 gap-3">
                {features.map(({ icon: Icon, label }) => (
                  <div key={label} className="bg-gray-50 rounded-2xl p-4 flex flex-col items-center text-center gap-3 border border-gray-100">
                    <div className="w-10 h-10 rounded-full bg-[#1c2951] flex items-center justify-center">
                      <Icon size={18} className="text-white" />
                    </div>
                    <p className="text-gray-600 text-xs leading-snug">{label}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Right — Phone mockup */}
            <div className="flex justify-center lg:justify-end">
              <div className="relative group cursor-pointer">
                <div
                  className="rounded-[2.5rem] overflow-hidden shadow-2xl border-4 border-gray-800 bg-white group-hover:-translate-y-4 group-hover:rotate-1 group-hover:shadow-[0_30px_60px_rgba(0,0,0,0.25)] transition-all duration-700 ease-out"
                  style={{ width: '220px', height: '440px' }}
                >
                  {/* Mock phone screen */}
                  <div className="bg-[#1c2951] h-16 flex items-center px-4 gap-3 group-hover:bg-[#c8102e] transition-colors duration-700">
                    <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center">
                      <span className="text-[#c8102e] font-black text-sm">BH</span>
                    </div>
                    <div>
                      <div className="text-white font-bold text-sm">BH MOBILE</div>
                      <div className="text-white/80 text-xs">BH BANK</div>
                    </div>
                  </div>
                  <div className="p-4">
                    <div className="flex gap-2 mb-3">
                      <div className="text-yellow-400 text-sm">★ 5.3</div>
                      <div className="text-gray-400 text-xs">16K avis</div>
                    </div>
                    <div className="bg-blue-500 text-white text-center py-2 rounded-full text-sm font-semibold mb-4 hover:bg-blue-600 transition-colors">
                      Télécharger
                    </div>
                    <div className="space-y-2">
                      {[1, 2, 3].map((i) => (
                        <div
                          key={i}
                          className="h-16 bg-gray-100 rounded-lg group-hover:bg-gray-200 transition-colors duration-700 delay-100"
                        />
                      ))}
                    </div>
                  </div>
                </div>

                {/* Decorative glow */}
                <div
                  className="absolute -inset-4 rounded-[3rem] -z-10 opacity-20 blur-2xl group-hover:opacity-40 transition-opacity duration-700"
                  style={{ background: 'linear-gradient(135deg, #c8102e, #1c2951)' }}
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section 3: Digital product logos band ── */}
      <section className="bg-[#1c2951] py-6">
        <div className="max-w-screen-xl mx-auto px-6">
          <div className="flex justify-center gap-8 items-center flex-wrap">
            {digitalProducts.map((p) => (
              <a
                key={p.name}
                href="#"
                className="bg-white rounded-2xl flex items-center justify-center hover:shadow-lg transition-all hover:-translate-y-0.5"
                style={{ width: '110px', height: '80px' }}
              >
                <div
                  className="font-black text-center leading-tight"
                  style={{ fontSize: '13px', color: p.color, whiteSpace: 'pre-line' }}
                >
                  {p.logo}
                </div>
              </a>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
