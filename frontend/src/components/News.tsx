import { ArrowRight } from 'lucide-react';

const featured = {
  date: '10 avril, 2026',
  title: 'Engagement durable : la BH BANK enchaine avec le lancement de son projet structurant de bilan carbone',
  excerpt: 'La BH Bank enchaine avec le lancement de son projet structurant de bilan carbone, une initiative forte en faveur du développement durable.',
  image: 'https://images.pexels.com/photos/3184418/pexels-photo-3184418.jpeg?auto=compress&cs=tinysrgb&w=800',
};

const articles = [
  {
    date: '24 février, 2026',
    title: 'Appel à candidature administrateur indépendant P.C.R',
    excerpt: 'APPEL À CANDIDATURE ADM.IND P.C.R',
    image: 'https://images.pexels.com/photos/6804068/pexels-photo-6804068.jpeg?auto=compress&cs=tinysrgb&w=400',
  },
  {
    date: '15 janvier, 2026',
    title: 'La BH BANK réaffirme sa politique de proximité et son adhésion à la politique sociale de l\'État',
    excerpt: 'La BH BANK réaffirme sa politique de proximité et son adhésion à la politique sociale de l\'État.',
    image: 'https://images.pexels.com/photos/3184338/pexels-photo-3184338.jpeg?auto=compress&cs=tinysrgb&w=400',
  },
  {
    date: '18 décembre, 2025',
    title: 'La BH BANK soutient la création cinématographique',
    excerpt: 'La BH BANK soutient la création cinématographique à travers un partenariat stratégique.',
    image: 'https://images.pexels.com/photos/7821745/pexels-photo-7821745.jpeg?auto=compress&cs=tinysrgb&w=400',
  },
];

export default function News() {
  return (
    <section className="py-14 bg-white">
      <div className="max-w-screen-xl mx-auto px-6">
        {/* Header row */}
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-3xl font-black text-[#1c2951]">Actualités</h2>
          <a
            href="#"
            className="bg-[#1c2951] text-white px-6 py-2.5 rounded-full text-sm font-semibold hover:bg-[#263766] transition-colors whitespace-nowrap"
          >
            Voir toutes les actualités
          </a>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* LEFT — Featured big article */}
          <a href="#" className="group block h-full">
            <div className="rounded-2xl overflow-hidden mb-4 aspect-[4/3] shadow-md group-hover:shadow-2xl transition-all duration-500 group-hover:-translate-y-1">
              <img
                src={featured.image}
                alt={featured.title}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
              />
            </div>
            <div className="px-2">
              <p className="text-gray-500 text-sm mb-2">{featured.date}</p>
              <h3 className="text-xl font-black text-[#1c2951] leading-snug group-hover:text-[#c8102e] transition-colors duration-300">
                {featured.title}
              </h3>
              <p className="text-gray-500 text-sm mt-2 leading-relaxed">{featured.excerpt}</p>
            </div>
          </a>

          {/* RIGHT — 3 small articles */}
          <div className="flex flex-col gap-4">
            {articles.map((article, i) => (
              <a
                key={i}
                href="#"
                className="group flex items-center gap-4 bg-white p-3 rounded-2xl border border-transparent hover:border-gray-100 hover:shadow-lg transition-all duration-300 hover:-translate-y-1"
              >
                <div className="flex-1 min-w-0 px-2">
                  <p className="text-gray-400 text-xs mb-1">{article.date}</p>
                  <h4 className="text-[#1c2951] font-bold text-sm leading-snug group-hover:text-[#c8102e] transition-colors duration-300 mb-1">
                    {article.title}
                  </h4>
                  <p className="text-gray-400 text-xs leading-relaxed line-clamp-2">{article.excerpt}</p>
                  <div className="flex items-center gap-1 text-[#c8102e] text-xs font-semibold mt-2 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300">
                    Lire la suite <ArrowRight size={11} />
                  </div>
                </div>
                <div className="w-24 h-24 rounded-xl overflow-hidden shrink-0 shadow-sm group-hover:shadow-md transition-shadow">
                  <img
                    src={article.image}
                    alt={article.title}
                    className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
                  />
                </div>
              </a>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
