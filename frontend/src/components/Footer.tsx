import { Phone, Mail, MapPin, Linkedin, Instagram, Facebook, Youtube } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="bg-[#1c2951] text-gray-300 pt-16 pb-8">
      <div className="max-w-screen-xl mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-10">
          {/* Logo & Contact col */}
          <div className="lg:col-span-2 pr-8">
            <div className="mb-8">
              <a href="#" className="inline-block bg-white px-3 py-2 rounded-lg mb-8">
                <img src="/logobh.svg" alt="BH Bank" className="h-[36px] w-auto" />
              </a>
              <p className="text-gray-400 text-xs leading-relaxed mb-8">
                BH Bank, Votre partenaire financier pour des<br />
                solutions sur mesure et un service de qualité. Vers<br />
                de nouvelles perspectives.
              </p>
              
              <div className="flex gap-4">
                {[Linkedin, Instagram, Facebook, Youtube].map((Icon, i) => (
                  <a
                    key={i}
                    href="#"
                    className="w-10 h-10 rounded-full border border-gray-600 flex items-center justify-center hover:bg-[#c8102e] hover:border-[#c8102e] hover:text-white transition-all text-gray-300"
                  >
                    <Icon size={16} />
                  </a>
                ))}
              </div>
            </div>

            {/* Nous contacter */}
            <div className="mb-8">
              <h4 className="text-[#c8102e] font-bold text-lg mb-4">Nous contacter</h4>
              <ul className="space-y-4">
                <li>
                  <a href="#" className="flex items-center gap-3 text-sm text-gray-300 hover:text-white transition-colors">
                    <Phone size={16} className="text-[#c8102e]" />
                    (+216) 71 126 000
                  </a>
                </li>
                <li>
                  <a href="#" className="flex items-center gap-3 text-sm text-gray-300 hover:text-white transition-colors">
                    <Mail size={16} className="text-[#c8102e]" />
                    Contact@bhbank.tn
                  </a>
                </li>
                <li>
                  <a href="#" className="flex items-start gap-3 text-sm text-gray-300 hover:text-white transition-colors">
                    <MapPin size={16} className="text-[#c8102e] mt-0.5" />
                    18 Avenue Mohamed V Tunis 1023
                  </a>
                </li>
              </ul>
            </div>

            {/* Médiateur */}
            <div>
              <h4 className="text-[#c8102e] font-bold text-lg mb-4">Médiateur</h4>
              <p className="text-gray-300 text-sm mb-4">Meftah Ziadi</p>
              <ul className="space-y-4">
                <li>
                  <a href="#" className="flex items-center gap-3 text-sm text-gray-300 hover:text-white transition-colors">
                    <Phone size={16} className="text-[#c8102e]" />
                    (+216) 50428037 / 94371576
                  </a>
                </li>
                <li>
                  <a href="#" className="flex items-center gap-3 text-sm text-gray-300 hover:text-white transition-colors">
                    <Mail size={16} className="text-[#c8102e]" />
                    ziadi.meftah@cbf.org.tn
                  </a>
                </li>
                <li>
                  <a href="#" className="flex items-start gap-3 text-sm text-gray-300 hover:text-white transition-colors">
                    <MapPin size={16} className="text-[#c8102e] mt-0.5" />
                    20, rue Mohamed Triki - 2037 - Ennasr<br />2
                  </a>
                </li>
              </ul>
            </div>
          </div>

          {/* Column 2 */}
          <div className="space-y-12">
            <div>
              <h4 className="text-[#c8102e] font-bold text-lg mb-6 leading-tight">
                Chartes, codes et<br />
                politiques
              </h4>
              <ul className="space-y-3">
                {['Chartes', 'Codes', 'Politiques'].map(item => (
                  <li key={item} className="flex items-center justify-between border-b border-gray-700 pb-2 cursor-pointer hover:text-white transition-colors">
                    <span className="text-sm">{item}</span>
                    <span>+</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="text-[#c8102e] font-bold text-lg mb-6 leading-tight">
                Conseil d'administration /<br />
                direction générale
              </h4>
              <a href="#" className="text-sm text-white hover:text-gray-300 transition-colors">
                Conseil d'administration &<br />direction générale
              </a>
            </div>
            <div>
              <h4 className="text-[#c8102e] font-bold text-lg mb-4">Liens utiles</h4>
              <ul className="space-y-3">
                {['Actualités', 'Foire aux questions', 'Recrutement', 'Plan du site'].map(item => (
                  <li key={item}>
                    <a href="#" className="text-sm text-white hover:text-gray-300 transition-colors">{item}</a>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Column 3 */}
          <div className="space-y-12">
            <div>
              <h4 className="text-[#c8102e] font-bold text-lg mb-6">Documents AGO</h4>
              <ul className="space-y-4">
                <li><a href="#" className="text-sm text-white hover:text-gray-300 transition-colors">Convocation AGO 2025</a></li>
                <li><a href="#" className="text-sm text-white hover:text-gray-300 transition-colors">Rapport annuel 2024 _FR</a></li>
                <li><a href="#" className="text-sm text-white hover:text-gray-300 transition-colors">Rapport annuel 2024 _AR</a></li>
                <li><a href="#" className="text-sm text-white hover:text-gray-300 transition-colors">Communique AGO 2024</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-[#c8102e] font-bold text-lg mb-6">Publications</h4>
              <ul className="space-y-4">
                <li><a href="#" className="text-sm text-white hover:text-gray-300 transition-colors">Infos financières</a></li>
                <li><a href="#" className="text-sm text-white hover:text-gray-300 transition-colors">Rapports annuels</a></li>
                <li><a href="#" className="text-sm text-white hover:text-gray-300 transition-colors">Communiqués</a></li>
                <li><a href="#" className="text-sm text-white hover:text-gray-300 transition-colors">Appels d'offres</a></li>
                <li><a href="#" className="text-sm text-white hover:text-gray-300 transition-colors">Nos tarifs</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-[#c8102e] font-bold text-lg mb-4">Centre relation client</h4>
              <ul className="space-y-4">
                <li><a href="#" className="text-sm text-white hover:text-gray-300 transition-colors">Portail réclamations</a></li>
                <li><a href="#" className="text-sm text-white hover:text-gray-300 transition-colors">Nos délais</a></li>
              </ul>
            </div>
          </div>

          {/* Column 4 */}
          <div className="space-y-12">
            <div>
              <h4 className="text-[#c8102e] font-bold text-lg mb-6">Responsabilité sociétale</h4>
              <ul className="space-y-4">
                <li><a href="#" className="text-sm text-white hover:text-gray-300 transition-colors">RSE BH BANK</a></li>
                <li><a href="#" className="text-sm text-white hover:text-gray-300 transition-colors">SGES de la BH BANK</a></li>
                <li><a href="#" className="text-sm text-white hover:text-gray-300 transition-colors">Politique environnementale et<br />sociale RSE</a></li>
                <li><a href="#" className="text-sm text-white hover:text-gray-300 transition-colors">Rapport de durabilité 2024</a></li>
                <li><a href="#" className="text-sm text-white hover:text-gray-300 transition-colors">Charte RSE Fournisseur</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-[#c8102e] font-bold text-lg mb-6">Accès à l'information</h4>
              <ul className="space-y-4">
                <li><a href="#" className="text-sm text-white hover:text-gray-300 transition-colors">Droit d'accès à l'information</a></li>
                <li><a href="#" className="text-sm text-white hover:text-gray-300 transition-colors">Documents utiles</a></li>
              </ul>
            </div>
          </div>
        </div>
        
        {/* Copyright separator */}
        <div className="mt-16 pt-6 border-t border-gray-700 flex flex-col md:flex-row items-center justify-between text-xs text-gray-500">
             <p>&copy; {new Date().getFullYear()} BH Bank — Banque de l'Habitat. Tous droits réservés.</p>
        </div>
      </div>
    </footer>
  );
}
