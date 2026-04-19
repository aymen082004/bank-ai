import { useState, useEffect, useCallback } from 'react';

const slides = [
  {
    id: 1,
    image: 'https://images.pexels.com/photos/1546168/pexels-photo-1546168.jpeg?auto=compress&cs=tinysrgb&w=1600',
    titleAr: 'صندوق النهوض بالمسكن\nلفائدة الأجراء',
    subtitleAr: 'تمويل شراء أو بناء مسكن\nبشروط ميسرة لفائدة الأجراء',
    titleFr: '',
    subtitleFr: '',
    lang: 'ar',
  },
  {
    id: 2,
    image: 'https://images.pexels.com/photos/3769021/pexels-photo-3769021.jpeg?auto=compress&cs=tinysrgb&w=1600',
    titleAr: 'قروض إستهلاك\nبشروط ميسرة\nلتمويل شراءاتكم',
    subtitleAr: '',
    titleFr: '',
    subtitleFr: '',
    lang: 'ar',
  },
  {
    id: 3,
    image: 'https://images.pexels.com/photos/6801648/pexels-photo-6801648.jpeg?auto=compress&cs=tinysrgb&w=1600',
    titleAr: '',
    subtitleAr: '',
    titleFr: 'Découvrez BH Net',
    subtitleFr: 'Votre banque à portée de main,\n24h/24 et 7j/7',
    lang: 'fr',
  },
  {
    id: 4,
    image: 'https://images.pexels.com/photos/280229/pexels-photo-280229.jpeg?auto=compress&cs=tinysrgb&w=1600',
    titleAr: 'برنامج السكن الاجتماعي\nللطبقة الوسطى',
    subtitleAr: 'حلول تمويل عقاري\nبأفضل الشروط',
    titleFr: '',
    subtitleFr: '',
    lang: 'ar',
  },
];

export default function Hero() {
  const [current, setCurrent] = useState(0);
  const [fading, setFading] = useState(false);

  const goTo = useCallback(
    (idx: number) => {
      if (fading) return;
      setFading(true);
      setTimeout(() => {
        setCurrent(idx);
        setFading(false);
      }, 400);
    },
    [fading],
  );

  useEffect(() => {
    const t = setInterval(() => goTo((current + 1) % slides.length), 6000);
    return () => clearInterval(t);
  }, [current, goTo]);

  const slide = slides[current];
  const isAr = slide.lang === 'ar';

  return (
    <section className="relative w-full overflow-hidden" style={{ height: 'clamp(380px, 52vw, 540px)' }}>
      {/* Background image — full width */}
      <div
        className="absolute inset-0 transition-opacity duration-700 ease-in-out"
        style={{ opacity: fading ? 0 : 1 }}
      >
        <img
          src={slide.image}
          alt=""
          className={`w-full h-full object-cover transition-transform duration-[6000ms] ${fading ? 'scale-100' : 'scale-105'}`}
        />
        {/* Dark overlay */}
        <div
          className="absolute inset-0"
          style={{
            background: isAr
              ? 'linear-gradient(to left, rgba(0,0,0,0.72) 45%, rgba(0,0,0,0.15) 100%)'
              : 'linear-gradient(to right, rgba(0,0,0,0.72) 45%, rgba(0,0,0,0.15) 100%)',
          }}
        />
      </div>

      {/* Text content */}
      <div
        className={`absolute inset-0 flex items-center transition-all duration-700 ease-out transform ${fading ? 'opacity-0 translate-y-8' : 'opacity-100 translate-y-0'}`}
      >
        <div className="w-full max-w-screen-xl mx-auto px-6 flex">
          {/* Arabic slide */}
          {isAr && (
            <div className="ml-auto text-right" dir="rtl" style={{ maxWidth: '520px' }}>
              {slide.titleAr && (
                <h1
                  className="text-white font-bold leading-tight whitespace-pre-line mb-4"
                  style={{
                    fontSize: 'clamp(26px, 3.5vw, 48px)',
                    fontFamily: "'Amiri', serif",
                    textShadow: '0 2px 8px rgba(0,0,0,0.5)',
                  }}
                >
                  {slide.titleAr}
                </h1>
              )}
              {slide.subtitleAr && (
                <p
                  className="text-gray-200 leading-relaxed whitespace-pre-line"
                  style={{
                    fontSize: 'clamp(16px, 2vw, 26px)',
                    fontFamily: "'Amiri', serif",
                  }}
                >
                  {slide.subtitleAr}
                </p>
              )}
            </div>
          )}

          {/* French slide */}
          {!isAr && (
            <div className="mr-auto text-left" style={{ maxWidth: '520px' }}>
              {slide.titleFr && (
                <h1
                  className="text-white font-black leading-tight whitespace-pre-line mb-4"
                  style={{ fontSize: 'clamp(28px, 3.5vw, 52px)', textShadow: '0 2px 8px rgba(0,0,0,0.5)' }}
                >
                  {slide.titleFr}
                </h1>
              )}
              {slide.subtitleFr && (
                <p
                  className="text-gray-200 leading-relaxed whitespace-pre-line mb-6"
                  style={{ fontSize: 'clamp(14px, 1.5vw, 18px)' }}
                >
                  {slide.subtitleFr}
                </p>
              )}
              <a
                href="#"
                className="inline-block bg-[#c8102e] text-white px-7 py-3 rounded-full text-sm font-semibold hover:bg-red-700 transition-all"
              >
                En savoir plus
              </a>
            </div>
          )}
        </div>

        {/* Red accent square — right edge, matching real site */}
        <div
          className="absolute right-0 top-1/2 -translate-y-1/2 bg-[#c8102e]"
          style={{ width: '10px', height: '80px' }}
        />
      </div>

      {/* Dot pagination */}
      <div className="absolute bottom-5 left-1/2 -translate-x-1/2 z-20 flex items-center gap-2">
        {slides.map((_, i) => (
          <button
            key={i}
            onClick={() => goTo(i)}
            className="rounded-full transition-all duration-300"
            style={{
              width: i === current ? '20px' : '8px',
              height: '8px',
              backgroundColor: i === current ? '#c8102e' : 'rgba(255,255,255,0.6)',
            }}
            aria-label={`Slide ${i + 1}`}
          />
        ))}
      </div>
    </section>
  );
}
