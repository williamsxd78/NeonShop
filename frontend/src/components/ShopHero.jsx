import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { imgSrc } from "@/lib/api";

export const ShopHero = ({ hero, count }) => (
  <div data-testid="shop-hero" className="relative -mx-4 mb-6 overflow-hidden sm:mx-0 sm:rounded-2xl sm:border sm:border-[#272B29]">
    <img src={imgSrc(hero.image)} alt="" className="absolute inset-0 h-full w-full object-cover object-right" />
    <div className="absolute inset-0 bg-gradient-to-r from-[#0A0B0B] via-[#0A0B0B]/70 to-transparent" />
    <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-[#0A0B0B] to-transparent" />
    <div className="relative px-6 py-12 sm:px-10 sm:py-16">
      <h1 data-testid="shop-hero-title" className="bg-gradient-to-r from-[#4ADE80] to-[#22C55E] bg-clip-text font-display text-4xl font-semibold uppercase tracking-[0.08em] text-transparent sm:text-6xl">{hero.title}</h1>
      {hero.subtitle && <p data-testid="shop-hero-subtitle" className="mt-2 text-base text-slate-300 sm:text-lg">{hero.subtitle.replace("{count}", count)}</p>}
    </div>
  </div>
);

const BannerLink = ({ link, children, ...rest }) =>
  !link ? <div {...rest}>{children}</div>
    : link.startsWith("/") ? <Link to={link} {...rest}>{children}</Link>
    : <a href={link} target="_blank" rel="noopener noreferrer" {...rest}>{children}</a>;

export function BannerCarousel({ banners }) {
  const ref = useRef(null);
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    if (banners.length < 2) return;
    const t = setInterval(() => setIdx((i) => (i + 1) % banners.length), 6000);
    return () => clearInterval(t);
  }, [banners.length]);
  useEffect(() => {
    const el = ref.current;
    if (el) el.scrollTo({ left: el.clientWidth * idx, behavior: "smooth" });
  }, [idx]);
  if (!banners.length) return null;
  return (
    <div className="mb-6" data-testid="shop-banners">
      <div ref={ref} className="no-scrollbar flex snap-x snap-mandatory overflow-x-auto rounded-2xl"
        onScroll={(e) => { const w = e.currentTarget.clientWidth; const i = Math.round(e.currentTarget.scrollLeft / w); if (i !== idx) setIdx(i); }}>
        {banners.map((b) => (
          <BannerLink key={b.id} link={b.link} data-testid={`shop-banner-${b.id}`}
            className="relative flex min-h-[150px] w-full shrink-0 snap-start items-center overflow-hidden rounded-2xl border border-[#272B29] sm:min-h-[180px]">
            <img src={imgSrc(b.image)} alt="" className="absolute inset-0 h-full w-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-r from-[#0A0B0B]/95 via-[#0A0B0B]/60 to-transparent" />
            <div className="relative max-w-[75%] p-5 sm:p-7">
              {b.title && <div className="font-display text-lg text-slate-100 sm:text-xl">{b.title}</div>}
              {b.subtitle && <p className="mt-1 text-xs text-slate-400 sm:text-sm">{b.subtitle}</p>}
              {b.button_text && <span className="mt-3 inline-flex items-center gap-1 rounded-lg bg-[#22C55E] px-3 py-1.5 text-xs font-semibold text-[#06140C]">{b.button_text}<ArrowRight size={13} /></span>}
            </div>
          </BannerLink>
        ))}
      </div>
      {banners.length > 1 && (
        <div className="mt-2 flex justify-center gap-1.5">{banners.map((b, i) => (
          <button key={b.id} data-testid={`shop-banner-dot-${i}`} onClick={() => setIdx(i)} className={`h-1.5 rounded-full transition-all ${i === idx ? "w-5 bg-[#22C55E]" : "w-1.5 bg-slate-600"}`} />
        ))}</div>
      )}
    </div>
  );
}
