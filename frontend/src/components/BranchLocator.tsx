import { useState } from 'react';
import { Search, MapPin } from 'lucide-react';

const gouvernorats = [
  'Ariana', 'Béja', 'Ben Arous', 'Bizerte', 'Gabès', 'Gafsa',
  'Jendouba', 'Kairouan', 'Kasserine', 'Kébili', 'Kef', 'Mahdia',
  'Manouba', 'Médenine', 'Monastir', 'Nabeul', 'Sfax', 'Sidi Bouzid',
  'Siliana', 'Sousse', 'Tataouine', 'Tozeur', 'Tunis', 'Zaghouan',
];

// Mock agency pins on the "map"
const pins = [
  { top: '30%', left: '42%', size: 'lg' },
  { top: '45%', left: '55%', size: 'md' },
  { top: '20%', left: '65%', size: 'sm' },
  { top: '60%', left: '70%', size: 'md' },
  { top: '38%', left: '80%', size: 'lg' },
  { top: '52%', left: '88%', size: 'sm' },
];

export default function BranchLocator() {
  const [keyword, setKeyword] = useState('');
  const [gov, setGov] = useState('Gouvernorat');

  return (
    <section className="bg-white py-14">
      <div className="max-w-screen-xl mx-auto px-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
          {/* LEFT — Search panel */}
          <div>
            {/* Icon + Title */}
            <div className="flex items-center gap-3 mb-4">
              <span className="text-2xl">🏛</span>
              <h2 className="text-2xl font-black text-[#1c2951]">Nos agences</h2>
            </div>

            <p className="text-[#1c2951] font-bold text-base leading-snug mb-6">
              Trouver facilement l'agence la plus<br />
              proche de chez vous pour un<br />
              accompagnement Personnalisé
            </p>

            {/* Search inputs */}
            <div className="flex gap-3 mb-4 flex-wrap">
              <div className="relative flex-1 min-w-48">
                <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Mots clés..."
                  value={keyword}
                  onChange={e => setKeyword(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-full text-sm focus:outline-none focus:border-[#1c2951] focus:ring-2 focus:ring-[#1c2951]/20"
                />
              </div>
              <select
                value={gov}
                onChange={e => setGov(e.target.value)}
                className="border border-gray-200 rounded-full px-5 py-3 text-sm text-gray-600 focus:outline-none focus:border-[#1c2951] bg-white pr-8"
              >
                <option value="Gouvernorat">Gouvernorat</option>
                {gouvernorats.map(g => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>
            </div>

            <button className="flex items-center justify-center gap-2 bg-[#1c2951] text-white px-8 py-3 rounded-full font-semibold text-sm hover:bg-[#263766] transition-colors w-full sm:w-auto">
              <MapPin size={16} />
              Trouvez votre agence
            </button>
          </div>

          {/* RIGHT — Stylized map */}
          <div
            className="relative rounded-2xl overflow-hidden"
            style={{ height: '320px', background: 'linear-gradient(135deg, #e8eef8 0%, #dde6f2 100%)' }}
          >
            {/* Grid lines to simulate map */}
            <svg className="absolute inset-0 w-full h-full opacity-20" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1c2951" strokeWidth="0.5" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#grid)" />
            </svg>

            {/* Road lines */}
            <svg className="absolute inset-0 w-full h-full opacity-30" xmlns="http://www.w3.org/2000/svg">
              <path d="M 0 160 Q 200 140 400 180 T 800 160" stroke="#b0c4de" strokeWidth="6" fill="none" />
              <path d="M 200 0 Q 220 160 240 320" stroke="#b0c4de" strokeWidth="4" fill="none" />
              <path d="M 500 0 Q 520 160 540 320" stroke="#b0c4de" strokeWidth="4" fill="none" />
            </svg>

            {/* BH Agency pins */}
            {pins.map((pin, i) => (
              <div
                key={i}
                className="absolute flex items-center justify-center"
                style={{
                  top: pin.top,
                  left: pin.left,
                  transform: 'translate(-50%, -50%)',
                }}
              >
                {pin.size === 'lg' ? (
                  <div className="bg-[#c8102e] text-white rounded-b-full rounded-t-full flex items-center justify-center shadow-lg" style={{ width: '52px', height: '60px', clipPath: 'polygon(50% 100%, 0 40%, 0 0, 100% 0, 100% 40%)' }}>
                    <span className="font-black text-[11px] mt-1">BH</span>
                  </div>
                ) : pin.size === 'md' ? (
                  <div className="bg-[#c8102e]/70 text-white rounded-b-full rounded-t-full flex items-center justify-center shadow-md" style={{ width: '40px', height: '46px', clipPath: 'polygon(50% 100%, 0 40%, 0 0, 100% 0, 100% 40%)' }}>
                    <span className="font-black text-[9px] mt-1">BH</span>
                  </div>
                ) : (
                  <div className="bg-[#c8102e]/40 rounded-full" style={{ width: '14px', height: '14px' }} />
                )}
              </div>
            ))}

            {/* Subtle label */}
            <div className="absolute bottom-3 right-3 text-xs text-gray-400 bg-white/70 px-2 py-1 rounded-full">
              Carte des agences BH Bank
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
