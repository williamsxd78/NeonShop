import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Search, RefreshCw, ArrowLeft, X, SlidersHorizontal } from "lucide-react";
import { api, money } from "@/lib/api";
import { useSite } from "@/lib/site";
import { NoticeBox } from "@/components/NoticeBox";
import { ShopHero, BannerCarousel } from "@/components/ShopHero";
import { CategoryIcon } from "@/components/CategoryIcon";
import { useAuth } from "@/context/AuthContext";
import { ProductCard } from "@/components/ProductCard";
import { FeaturedVendors } from "@/pages/Vendors";
import { Empty } from "@/components/Shared";
import { TextSection, ColumnsSection } from "@/components/HomeSections";

const DEFAULT_ORDER = ["hero", "banners", "notice", "vendors", "products"].map((t) => ({ id: t, type: t, enabled: true }));

const SORTS = [["new", "Newest"], ["popular", "Best sellers"], ["price_asc", "Price: low → high"], ["price_desc", "Price: high → low"]];

export default function Marketplace() {
  const { user } = useAuth();
  const { categories, category_style: style, notice, hero, banners, product_count, sections } = useSite();
  const [params, setParams] = useSearchParams();
  const vendor = params.get("vendor") || "";
  const [items, setItems] = useState(null);
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");
  const [sort, setSort] = useState("new");
  const [tick, setTick] = useState(0);
  const [facets, setFacets] = useState([]);
  const [attrs, setAttrs] = useState({});
  const active = Object.values(attrs).filter(Boolean).length;

  useEffect(() => { setAttrs({}); api.get("/products/facets", { params: { category: cat, vendor } }).then((r) => setFacets(r.data)); }, [cat, vendor]);
  useEffect(() => {
    const t = setTimeout(() => {
      api.get("/products", { params: { q, category: cat, sort, vendor, attrs: active ? JSON.stringify(attrs) : "" } }).then((r) => setItems(r.data));
    }, 250);
    return () => clearTimeout(t);
  }, [q, cat, sort, vendor, tick, attrs, active]);

  const order = vendor ? [{ id: "products", type: "products" }] : sections || DEFAULT_ORDER;
  const heroShown = !vendor && hero?.enabled && order.some((x) => x.type === "hero");

  const products = (
    <div key="products" data-testid="home-section-products">
      <div className="mb-5 flex items-center gap-3 nk-rise">
        {vendor && <button onClick={() => setParams({})} data-testid="clear-vendor-filter" className="grid h-11 w-11 place-items-center rounded-xl border border-line bg-panel text-slate-300"><ArrowLeft size={18} /></button>}
        {!heroShown && <h1 className="font-display text-2xl font-semibold tracking-tight">{vendor && items?.[0] ? items[0].vendor_name : "Shop"}</h1>}
        <div className="ml-auto flex items-center gap-2">
          {user && <Link to="/wallet" data-testid="shop-balance" className="rounded-lg border border-line bg-surface px-3 py-2 font-mono text-xs text-slate-500">Balance <span className="ml-1 font-semibold text-brandlt">{money(user.balance_cents)}</span></Link>}
          {user && <Link to="/vault" data-testid="shop-my-keys" className="hidden rounded-lg border border-line bg-panel px-3 py-2 text-xs font-semibold text-slate-300 sm:block">My Keys</Link>}
        </div>
      </div>

      <div className="mb-4 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search size={17} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
          <input data-testid="market-search-input" className="nk-input rounded-xl py-3 pl-11" placeholder="Search product, vendor, category…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <select data-testid="market-sort-select" className="nk-input rounded-xl sm:w-52" value={sort} onChange={(e) => setSort(e.target.value)}>
          {SORTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      </div>

      <div className="no-scrollbar mb-5 flex gap-2 overflow-x-auto">
        {["", ...categories].map((c) => {
          const st = c ? style[c] || {} : { color: "rgb(var(--nk-brand))" };
          const on = cat === c;
          return (
            <button key={c || "all"} data-testid={`category-tab-${(c || "all").toLowerCase().replace(/ /g, "-")}`} onClick={() => setCat(c)}
              style={on ? { borderColor: `color-mix(in srgb, ${st.color} 60%, transparent)`, background: `color-mix(in srgb, ${st.color} 12%, transparent)`, color: st.color } : undefined}
              className={`flex items-center gap-2 whitespace-nowrap rounded-lg border px-4 py-2 text-sm transition-colors ${on ? "" : "border-line bg-panel text-slate-400 hover:text-white"}`}>
              {c && <CategoryIcon name={st.icon} size={14} style={on ? undefined : { color: st.color }} />}
              {c || "All"}
            </button>
          );
        })}
      </div>

      {facets.length > 0 && (
        <div data-testid="attr-filters" className="mb-5 flex flex-wrap items-center gap-2">
          <span className="flex items-center gap-1.5 font-mono text-xs uppercase tracking-wider text-slate-500"><SlidersHorizontal size={14} />Filters</span>
          {facets.map((f) => {
            const slug = f.key.toLowerCase().replace(/[^a-z0-9]+/g, "-");
            return (
              <select key={f.key} data-testid={`attr-filter-${slug}`} value={attrs[f.key] || ""} onChange={(e) => setAttrs({ ...attrs, [f.key]: e.target.value })}
                className={`rounded-lg border bg-panel px-3 py-2 text-sm outline-none ${attrs[f.key] ? "border-brand/60 text-brandlt" : "border-line text-slate-300"}`}>
                <option value="">{f.key}: all</option>
                {f.values.map((v) => <option key={v.value} value={v.value}>{`${v.value} (${v.count})`}</option>)}
              </select>
            );
          })}
          {active > 0 && <button data-testid="attr-filters-clear" onClick={() => setAttrs({})} className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-white"><X size={13} />Clear ({active})</button>}
        </div>
      )}

      <div className="mb-4 flex items-center justify-between">
        <span data-testid="products-count" className="font-mono text-sm text-slate-500">{items ? `${items.length} products found` : "Loading…"}</span>
        <button data-testid="refresh-products" onClick={() => setTick(tick + 1)} className="text-slate-500 hover:text-white"><RefreshCw size={16} /></button>
      </div>

      {items === null ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{[...Array(6)].map((_, i) => <div key={i} className="nk-card h-48 animate-pulse" />)}</div>
      ) : items.length === 0 ? (
        <Empty testId="market-empty" text="No products match your filters." />
      ) : (
        <div data-testid="product-grid" className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((p, i) => <ProductCard key={p.id} p={p} i={i} />)}
        </div>
      )}
      {vendor && <button onClick={() => setParams({})} className="mt-6 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-white"><X size={14} />Clear vendor filter</button>}
    </div>
  );

  const render = (x) => {
    if (x.type === "products") return products;
    if (x.type === "hero") return heroShown ? <ShopHero key={x.id} hero={hero} count={product_count} /> : null;
    if (x.type === "banners") return <BannerCarousel key={x.id} banners={banners} />;
    if (x.type === "notice") return notice?.active ? <div key={x.id} className="mb-6"><NoticeBox n={notice} /></div> : null;
    if (x.type === "vendors") return <FeaturedVendors key={x.id} />;
    if (x.type === "text") return <TextSection key={x.id} s={x} />;
    if (x.type === "columns") return <ColumnsSection key={x.id} s={x} />;
    return null;
  };
  return <div>{order.map(render)}</div>;
}
