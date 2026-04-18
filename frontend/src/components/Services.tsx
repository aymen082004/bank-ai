import { Home, Briefcase, TrendingUp, Shield, CreditCard, Users } from 'lucide-react';

const services = [
  {
    icon: Home,
    title: 'Crédit Immobilier',
    description: "Financez l'acquisition de votre bien immobilier avec nos solutions adaptées.",
    color: 'bg-red-50',
    iconColor: 'text-[#c8102e]',
    border: 'border-red-100',
  },
  {
    icon: CreditCard,
    title: 'Comptes & Cartes',
    description: 'Ouvrez votre compte et profitez de nos cartes bancaires pour toutes vos dépenses.',
    color: 'bg-blue-50',
    iconColor: 'text-blue-600',
    border: 'border-blue-100',
  },
  {
    icon: TrendingUp,
    title: 'Épargne & Placements',
    description: "Faites fructifier votre argent avec nos produits d'épargne et d'investissement.",
    color: 'bg-emerald-50',
    iconColor: 'text-emerald-600',
    border: 'border-emerald-100',
  },
  {
    icon: Briefcase,
    title: 'Solutions Entreprises',
    description: "Accompagnez votre activité avec nos offres dédiées aux professionnels et TPE/PME.",
    color: 'bg-amber-50',
    iconColor: 'text-amber-600',
    border: 'border-amber-100',
  },
  {
    icon: Shield,
    title: 'Assurances',
    description: 'Protégez votre patrimoine, votre famille et votre activité avec nos couvertures.',
    color: 'bg-sky-50',
    iconColor: 'text-sky-600',
    border: 'border-sky-100',
  },
  {
    icon: Users,
    title: 'Banque Privée',
    description: 'Un service personnalisé et exclusif pour la gestion de votre patrimoine.',
    color: 'bg-rose-50',
    iconColor: 'text-rose-600',
    border: 'border-rose-100',
  },
];

export default function Services() {
  return (
    <section className="py-20 bg-white">
      <div className="max-w-7xl mx-auto px-4">
        <div className="text-center mb-14">
          <span className="text-[#c8102e] font-semibold text-sm uppercase tracking-widest">Nos Services</span>
          <h2 className="text-3xl md:text-4xl font-black text-gray-900 mt-2">
            Des solutions pour chaque besoin
          </h2>
          <p className="text-gray-500 mt-4 max-w-2xl mx-auto leading-relaxed">
            BH Bank vous accompagne à chaque étape de votre vie avec une gamme complète de produits et services bancaires.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {services.map((service) => {
            const Icon = service.icon;
            return (
              <a
                key={service.title}
                href="#"
                className={`group p-6 rounded-2xl border ${service.border} ${service.color} hover:shadow-lg hover:-translate-y-1 transition-all duration-300`}
              >
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center bg-white shadow-sm mb-4 ${service.iconColor}`}>
                  <Icon size={22} />
                </div>
                <h3 className="font-bold text-gray-900 text-lg mb-2 group-hover:text-[#c8102e] transition-colors">
                  {service.title}
                </h3>
                <p className="text-gray-500 text-sm leading-relaxed">{service.description}</p>
                <span className={`inline-block mt-4 text-sm font-semibold ${service.iconColor} group-hover:underline`}>
                  En savoir plus &rarr;
                </span>
              </a>
            );
          })}
        </div>
      </div>
    </section>
  );
}
