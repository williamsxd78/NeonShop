import { useState } from "react";
import { Link } from "react-router-dom";
import { BadgeCheck, Search, ExternalLink, Star } from "lucide-react";
import { useFetch } from "@/lib/useFetch";
import { PageHeader, Empty } from "@/components/Shared";

const Avatar = ({ name }) => (
  <div className="grid h-12 w-12 shrink-0 place-items-center rounded-xl border border-[#272B29] bg-[#22C55E]/10 font-display text-lg font-bold text-[#4ADE80]">{(name || "?")[0].toUpperCase()}</div>
);

const VendorCard = ({ v, featured }) => (
  <div data-testid={`vendor-card-${v.id}`} className={`nk-card nk-card-hover rounded-2xl p-5 ${featured ? "border-[#22C55E]/40" : ""}`}>
    <div className="flex items-start gap-3">
      <Avatar name={v.store_name || v.name} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className="truncate font-display font-semibold">{v.store_name || v.name}</span>
          <BadgeCheck size={16} className="shrink-0 text-[#4ADE80]" />
          {featured && <span className="ml-auto flex items-center gap-1 rounded-full bg-[#FFB800]/15 px-2 py-0.5 font-mono text-[10px] font-bold uppercase text-[#FFB800]"><Star size={10} />Featured</span>}
        </div>
        <p className="font-mono text-xs text-slate-500">{v.products} products · {v.sales} sales</p>
      </div>
    </div>
    <div className="mt-3 flex flex-wrap gap-1.5">
      {v.categories.map((c) => <span key={c} className="rounded-md bg-[#22D3EE]/10 px-2 py-0.5 font-mono text-[10px] uppercase text-[#22D3EE]">{c}</span>)}
    </div>
    <div className="mt-4 flex justify-end">
      <Link to={`/?vendor=${v.id}`} data-testid={`vendor-view-${v.id}`} className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#4ADE80] hover:underline"><ExternalLink size={14} />View products</Link>
    </div>
  </div>
);

export function FeaturedVendors() {
  const [list] = useFetch("/vendors");
  if (!list?.length) return null;
  return (
    <section className="mb-8" data-testid="featured-vendors">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="flex items-center gap-2 font-display text-lg font-bold"><BadgeCheck size={18} className="text-[#4ADE80]" />Verified vendors</h2>
        <Link to="/vendors" data-testid="all-vendors-link" className="text-sm text-[#4ADE80] hover:underline">All vendors</Link>
      </div>
      <div className="no-scrollbar grid auto-cols-[85%] grid-flow-col gap-4 overflow-x-auto sm:auto-cols-[46%] lg:auto-cols-[32%]">
        {list.slice(0, 6).map((v, i) => <VendorCard key={v.id} v={v} featured={i === 0} />)}
      </div>
    </section>
  );
}

export default function Vendors() {
  const [list] = useFetch("/vendors");
  const [q, setQ] = useState("");
  const shown = (list || []).filter((v) => `${v.store_name} ${v.categories.join(" ")}`.toLowerCase().includes(q.toLowerCase()));
  return (
    <div>
      <PageHeader eyebrow={`${list?.length ?? 0} vendors`} title="Verified vendors" />
      <div className="relative mb-6"><Search size={17} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
        <input data-testid="vendors-search-input" className="nk-input rounded-xl py-3 pl-11" placeholder="Search vendors, categories…" value={q} onChange={(e) => setQ(e.target.value)} /></div>
      {!shown.length ? <Empty testId="vendors-empty" text="No vendors found." /> : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" data-testid="vendors-grid">{shown.map((v, i) => <VendorCard key={v.id} v={v} featured={i === 0 && !q} />)}</div>
      )}
    </div>
  );
}
