import { useState } from "react";
import { Search, ChevronDown, Plus, Minus, Package } from "lucide-react";
import { money, fmtDate } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { StatusBadge, Stat, FilterTabs } from "@/components/Shared";
import { AdjustDialog } from "@/components/admin/AdminUsers";

function Details({ uid, onAdjusted }) {
  const [d, reload] = useFetch(`/admin/users/${uid}/details`);
  const [adjust, setAdjust] = useState(null);
  if (!d) return <div className="h-24 animate-pulse rounded-lg bg-[#121413]" />;
  const { user: u, stats, products, deposits } = d;
  const done = () => { reload(); onAdjusted(); };
  return (
    <div className="space-y-4" data-testid={`user-details-${uid}`}>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat label="Wallet balance" value={money(u.balance_cents)} testId={`ud-balance-${uid}`} />
        <Stat label="Products bought" value={stats.orders} accent="#E2E8F0" testId={`ud-orders-${uid}`} />
        <Stat label="Total spent" value={money(stats.spent_cents)} accent="#E2E8F0" testId={`ud-spent-${uid}`} />
        <Stat label="Deposited" value={money(stats.deposited_cents)} accent="#E2E8F0" testId={`ud-deposited-${uid}`} />
      </div>
      <div className="flex flex-wrap gap-2">
        <button data-testid={`ud-add-balance-${uid}`} onClick={() => setAdjust({ ...u, mode: "credit" })} className="nk-btn-primary nk-btn-sm"><Plus size={14} />Add balance</button>
        <button data-testid={`ud-deduct-balance-${uid}`} onClick={() => setAdjust({ ...u, mode: "debit" })} className="nk-btn-ghost nk-btn-sm"><Minus size={14} />Deduct</button>
        {u.role === "vendor" && <span className="self-center font-mono text-xs text-slate-400">Vendor earnings: {money(u.earnings_cents)}</span>}
      </div>
      <div>
        <div className="nk-label">Products bought</div>
        {!products.length ? <p className="text-xs text-slate-500" data-testid={`ud-no-products-${uid}`}>No purchases yet.</p> : (
          <div className="divide-y divide-[#272B29] rounded-lg border border-[#272B29]" data-testid={`ud-products-${uid}`}>
            {products.map((p) => (
              <div key={p.product_id} className="flex items-center gap-3 px-3 py-2 text-sm" data-testid={`ud-product-${p.product_id}`}>
                <Package size={14} className="shrink-0 text-[#22D3EE]" />
                <div className="min-w-0 flex-1"><div className="truncate text-slate-100">{p.title}</div><div className="text-[11px] text-slate-500">{p.category} · last {fmtDate(p.last_at)}</div></div>
                <span className="font-mono text-xs text-slate-400">×{p.count}</span>
                <span className="w-20 text-right font-mono text-xs text-[#4ADE80]">{money(p.spent_cents)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      {deposits.length > 0 && (
        <div>
          <div className="nk-label">Recent deposits</div>
          <div className="space-y-1">{deposits.slice(0, 5).map((x) => (
            <div key={x.id} className="flex items-center gap-3 text-xs"><span className="font-mono text-slate-400">{x.reference}</span><span className="font-mono">{x.coin}</span>
              <span className="font-mono text-[#4ADE80]">{money(x.credited_cents || x.amount_cents)}</span><StatusBadge status={x.status} /><span className="ml-auto text-slate-500">{fmtDate(x.created_at)}</span></div>
          ))}</div>
        </div>
      )}
      <AdjustDialog user={adjust} onClose={() => setAdjust(null)} onDone={done} />
    </div>
  );
}

export function AdminUserDetails() {
  const [role, setRole] = useState("all");
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(null);
  const [list, reload] = useFetch("/admin/users", { role, q });
  return (
    <div>
      <div className="relative mb-4"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
        <input data-testid="ud-search" className="nk-input pl-9" placeholder="Search name or email" value={q} onChange={(e) => setQ(e.target.value)} /></div>
      <FilterTabs value={role} onChange={setRole} options={["all", "buyer", "vendor", "admin"]} testPrefix="ud-filter" />
      <div className="space-y-2" data-testid="ud-list">
        {(list || []).map((u) => (
          <div key={u.id} className="nk-card overflow-hidden">
            <button data-testid={`ud-row-${u.id}`} onClick={() => setOpen(open === u.id ? null : u.id)} className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-white/[0.02]">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#22C55E]/10 font-display text-sm text-[#4ADE80]">{(u.name || u.email)[0].toUpperCase()}</div>
              <div className="min-w-0 flex-1"><div className="truncate text-sm text-slate-100">{u.name}</div><div className="truncate text-xs text-slate-500">{u.email}</div></div>
              <span className="hidden font-mono text-[10px] uppercase text-slate-500 sm:inline">{u.role}</span>
              <span className="font-mono text-xs text-[#4ADE80]">{money(u.balance_cents)}</span>
              <ChevronDown size={16} className={`text-slate-500 transition-transform ${open === u.id ? "rotate-180" : ""}`} />
            </button>
            {open === u.id && <div className="border-t border-[#272B29] p-4"><Details uid={u.id} onAdjusted={reload} /></div>}
          </div>
        ))}
        {list && !list.length && <p className="text-sm text-slate-500" data-testid="ud-empty">No users found.</p>}
      </div>
    </div>
  );
}
