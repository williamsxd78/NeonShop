import { Link } from "react-router-dom";
import { imgSrc } from "@/lib/api";
import { CategoryIcon } from "@/components/CategoryIcon";

const Cta = ({ s }) => {
  if (!s.button_text || !s.link) return null;
  const cls = "nk-btn-primary nk-btn-sm mt-4 w-fit";
  return s.link.startsWith("/")
    ? <Link to={s.link} className={cls} data-testid={`section-cta-${s.id}`}>{s.button_text}</Link>
    : <a href={s.link} target="_blank" rel="noopener noreferrer" className={cls} data-testid={`section-cta-${s.id}`}>{s.button_text}</a>;
};

export function TextSection({ s }) {
  return (
    <section className="nk-card mb-6 grid overflow-hidden md:grid-cols-[1fr_auto] nk-rise" data-testid={`home-section-${s.id}`}>
      <div className="flex flex-col justify-center p-6">
        {s.title && <h2 className="font-display text-xl">{s.title}</h2>}
        {s.body && <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-slate-400">{s.body}</p>}
        <Cta s={s} />
      </div>
      {s.image && <img src={imgSrc(s.image)} alt="" className="h-48 w-full object-cover md:h-full md:w-80" />}
    </section>
  );
}

export function ColumnsSection({ s }) {
  const cols = s.columns || [];
  return (
    <section className="mb-6 nk-rise" data-testid={`home-section-${s.id}`}>
      {s.title && <h2 className="mb-3 font-display text-xl">{s.title}</h2>}
      {s.body && <p className="mb-4 text-sm text-slate-400">{s.body}</p>}
      <div className={`grid gap-3 sm:grid-cols-2 ${cols.length >= 4 ? "lg:grid-cols-4" : cols.length === 3 ? "lg:grid-cols-3" : ""}`}>
        {cols.map((c, i) => (
          <div key={i} className="nk-card p-5" data-testid={`home-section-${s.id}-col-${i}`}>
            <span className="mb-3 grid h-10 w-10 place-items-center rounded-lg bg-brand/10 text-brand"><CategoryIcon name={c.icon} size={18} /></span>
            <div className="font-display text-base text-slate-100">{c.title}</div>
            <p className="mt-1 text-sm text-slate-400">{c.text}</p>
          </div>
        ))}
      </div>
      <Cta s={s} />
    </section>
  );
}
