import { useSearchParams } from "react-router-dom";
import { LayoutDashboard, ArrowDownToLine, ArrowUpFromLine, UserCheck, ListChecks, Settings, Users, ScrollText, Contact, MessageCircle, LayoutTemplate, Store, Palette, Rows3, PanelBottom, ArrowLeft, ChevronRight, Wand2 } from "lucide-react";
import VendorDashboard from "@/pages/VendorDashboard";
import { AdminSite } from "@/components/admin/AdminSite";
import { useFetch } from "@/lib/useFetch";
import { PageHeader } from "@/components/Shared";
import { AdminDeposits } from "@/components/admin/AdminDeposits";
import { AdminWithdrawals } from "@/components/admin/AdminWithdrawals";
import { AdminVendors } from "@/components/admin/AdminVendors";
import { AdminListings } from "@/components/admin/AdminListings";
import { AdminSettings } from "@/components/admin/AdminSettings";
import { AdminUsers } from "@/components/admin/AdminUsers";
import { AdminUserDetails } from "@/components/admin/AdminUserDetails";
import { AdminTickets } from "@/components/admin/AdminTickets";
import { AdminAudit, AdminOverview } from "@/components/admin/AdminAudit";
import { AdminBranding } from "@/components/admin/AdminBranding";
import { AdminSections } from "@/components/admin/AdminSections";
import { AdminFooter } from "@/components/admin/AdminFooter";

const GROUPS = [
  ["builder", "Website builder", [
    ["branding", "Name & colors", Palette, "Store name, logo, theme colors"],
    ["sections", "Home sections", Rows3, "Add, remove, reorder sections"],
    ["footer", "Footer", PanelBottom, "Footer columns and links"],
    ["site", "Shop content", LayoutTemplate, "Header, banners, notice, categories"],
  ]],
  ["requests", "Requests", [
    ["deposits", "Add-fund requests", ArrowDownToLine, "Verify crypto deposits"],
    ["withdrawals", "Withdrawal requests", ArrowUpFromLine, "Pay vendor payouts"],
    ["vendors", "Vendor requests", UserCheck, "Approve new sellers"],
    ["listings", "Listing requests", ListChecks, "Review products"],
    ["tickets", "Support tickets", MessageCircle, "Reply to users"],
  ]],
  ["manage", "Manage", [
    ["overview", "Overview", LayoutDashboard, "Stats and revenue"],
    ["store", "My store (sell)", Store, "List your own products"],
    ["settings", "Commission & wallets", Settings, "Fees and deposit addresses"],
    ["users", "Users", Users, "Roles, wallets, suspend"],
    ["userdetails", "User details", Contact, "Balances and purchases"],
    ["audit", "Audit log", ScrollText, "Every balance change"],
  ]],
];
const ALL = GROUPS.flatMap(([, , items]) => items);

function Tile({ k, label, Icon, sub, count, onOpen, big }) {
  return (
    <button data-testid={`admin-tab-${k}`} onClick={() => onOpen(k)}
      className={`nk-card nk-card-hover group flex items-center gap-3 p-4 text-left ${big ? "bg-surface" : ""}`}>
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-brand/10 text-brand"><Icon size={18} /></span>
      <div className="min-w-0 flex-1"><div className="truncate text-sm text-slate-100">{label}</div><div className="truncate text-[11px] text-slate-500">{sub}</div></div>
      {count > 0 && <span data-testid={`admin-tab-count-${k}`} className="rounded-full bg-[#FFB800] px-2 py-0.5 font-mono text-[10px] font-bold text-black">{count}</span>}
      <ChevronRight size={16} className="shrink-0 text-slate-600 transition-transform group-hover:translate-x-0.5" />
    </button>
  );
}

function Home({ pending, open }) {
  return (
    <div className="space-y-6 nk-rise" data-testid="admin-home">
      {GROUPS.map(([g, title, items]) => (
        <div key={g} data-testid={`admin-group-${g}`}
          className={g === "builder" ? "rounded-2xl border border-brand/30 bg-brand/[0.04] p-4 shadow-[0_0_30px_rgb(var(--nk-brand)/0.06)]" : ""}>
          <div className="mb-3 flex items-center gap-2">
            {g === "builder" && <Wand2 size={15} className="text-brand" />}
            <span className={g === "builder" ? "font-display text-base text-slate-100" : "nk-label mb-0"}>{title}</span>
            {g === "builder" && <span className="text-[11px] text-slate-500">Customize the look of your store</span>}
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {items.map(([k, l, I, sub]) => <Tile key={k} k={k} label={l} Icon={I} sub={sub} count={pending[k]} onOpen={open} big={g === "builder"} />)}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function AdminPanel() {
  const [sp, setSp] = useSearchParams();
  const tab = sp.get("s");
  const [stats, reloadStats] = useFetch("/admin/stats");
  const [settings, reloadSettings] = useFetch("/admin/settings");
  const pending = stats?.pending || {};
  const open = (k) => { setSp(k ? { s: k } : {}); window.scrollTo({ top: 0 }); };
  const cur = ALL.find(([k]) => k === tab);
  const CurIcon = cur?.[2];

  if (!cur) return (<div><PageHeader eyebrow="Control center" title="Admin panel" /><Home pending={pending} open={open} /></div>);
  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <button data-testid="admin-home-btn" onClick={() => open(null)} className="nk-btn-ghost nk-btn-sm"><ArrowLeft size={14} />Admin home</button>
        <h1 className="flex items-center gap-2 font-display text-xl" data-testid="admin-section-title"><CurIcon size={18} className="text-brand" />{cur[1]}</h1>
        <select data-testid="admin-jump" className="nk-input ml-auto w-full sm:w-60" value={tab} onChange={(e) => open(e.target.value)}>
          {GROUPS.map(([g, title, items]) => <optgroup key={g} label={title}>{items.map(([k, l]) => <option key={k} value={k}>{l}{pending[k] ? ` (${pending[k]})` : ""}</option>)}</optgroup>)}
        </select>
      </div>
      <section className="min-w-0 nk-rise" key={tab}>
        {tab === "overview" && <AdminOverview stats={stats} go={open} />}
        {tab === "deposits" && <AdminDeposits onChange={reloadStats} />}
        {tab === "withdrawals" && <AdminWithdrawals onChange={reloadStats} />}
        {tab === "vendors" && <AdminVendors onChange={reloadStats} globalPct={settings?.commission_pct} />}
        {tab === "listings" && <AdminListings onChange={reloadStats} />}
        {tab === "tickets" && <AdminTickets onChange={reloadStats} />}
        {tab === "settings" && <AdminSettings settings={settings} onSaved={reloadSettings} />}
        {tab === "store" && <VendorDashboard embedded />}
        {tab === "site" && <AdminSite />}
        {tab === "branding" && <AdminBranding />}
        {tab === "sections" && <AdminSections />}
        {tab === "footer" && <AdminFooter />}
        {tab === "users" && <AdminUsers />}
        {tab === "userdetails" && <AdminUserDetails />}
        {tab === "audit" && <AdminAudit />}
      </section>
    </div>
  );
}
