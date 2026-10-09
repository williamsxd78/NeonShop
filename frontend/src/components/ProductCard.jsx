import { Link } from "react-router-dom";
import { Package } from "lucide-react";
import { money, imgSrc } from "@/lib/api";

const tag = "rounded-md px-2 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider";

export const ProductCard = ({ p, i = 0 }) => (
  <Link to={`/product/${p.id}`} data-testid={`product-card-${p.id}`} style={{ animationDelay: `${i * 40}ms` }}
    className="nk-card nk-card-hover nk-rise group relative flex flex-col gap-4 overflow-hidden rounded-2xl p-5 pl-6">
    <span className="absolute inset-y-3 left-0 w-1 rounded-r-full bg-[#22D3EE]" />
    <div className="flex items-start gap-3">
      <div className="h-12 w-12 shrink-0 overflow-hidden rounded-xl border border-[#272B29] bg-[#22D3EE]/10">
        {p.image ? <img src={imgSrc(p.image)} alt="" className="h-full w-full object-cover" /> : <div className="grid h-full place-items-center text-[#22D3EE]"><Package size={20} /></div>}
      </div>
      <div className="min-w-0 flex-1">
        <h3 className="line-clamp-2 font-display text-base font-semibold leading-snug text-slate-100">{p.title}</h3>
        <p className="mt-0.5 truncate font-mono text-xs uppercase tracking-wide text-slate-500">{p.vendor_name}</p>
      </div>
    </div>
    <div className="flex flex-wrap gap-2">
      <span className={`${tag} bg-[#22D3EE]/10 text-[#22D3EE]`}>{p.category}</span>
      {p.stock_count > 0
        ? <span className={`${tag} bg-[#A855F7]/15 text-[#C084FC]`}>{p.stock_count} in stock</span>
        : <span className={`${tag} bg-[#FF2A5F]/10 text-[#FF2A5F]`}>sold out</span>}
      {p.sales_count > 0 && <span className={`${tag} text-slate-500`}>{p.sales_count} sold</span>}
    </div>
    <div className="mt-auto flex items-center justify-between">
      <span className="font-mono text-2xl font-semibold text-[#4ADE80]">{money(p.price_cents)}</span>
      <span className="nk-btn-buy nk-btn-sm px-5 py-2" data-testid={`product-card-buy-${p.id}`}>Buy</span>
    </div>
  </Link>
);
