import { useState } from "react";
import { LayoutDashboard, ArrowDownToLine, ArrowUpFromLine, UserCheck, ListChecks, Settings, Users, ScrollText, LayoutTemplate } from "lucide-react";
import { AdminSite } from "@/components/admin/AdminSite";
import { useFetch } from "@/lib/useFetch";
import { PageHeader } from "@/components/Shared";
import { AdminDeposits } from "@/components/admin/AdminDeposits";
import { AdminWithdrawals } from "@/components/admin/AdminWithdrawals";
import { AdminVendors } from "@/components/admin/AdminVendors";
import { AdminListings } from "@/components/admin/AdminListings";
import { AdminSettings } from "@/components/admin/AdminSettings";
import { AdminUsers } from "@/components/admin/AdminUsers";
import { AdminAudit, AdminOverview } from "@/components/admin/AdminAudit";

const SECTIONS = [
  ["overview", "Overview", LayoutDashboard],
  ["deposits", "Add-fund requests", ArrowDownToLine],
  ["withdrawals", "Withdrawal requests", ArrowUpFromLine],
  ["vendors", "Vendor requests", UserCheck],
  ["listings", "Listing requests", ListChecks],
  ["settings", "Commission & wallets", Settings],
  ["site", "Shop notice & categories", LayoutTemplate],
  ["users", "Users", Users],
  ["audit", "Audit log", ScrollText],
];

export default function AdminPanel() {
  const [tab, setTab] = useState("overview");
  const [stats, reloadStats] = useFetch("/admin/stats");
  const [settings, reloadSettings] = useFetch("/admin/settings");
  const pending = stats?.pending || {};

  return (
    <div>
      <PageHeader eyebrow="Control center" title="Admin panel" />
      <div className="grid gap-6 lg:grid-cols-[240px_1fr]">
        <aside className="no-scrollbar flex gap-2 overflow-x-auto lg:sticky lg:top-24 lg:h-fit lg:flex-col lg:overflow-visible">
          {SECTIONS.map(([k, l, Icon]) => (
            <button key={k} data-testid={`admin-tab-${k}`} onClick={() => setTab(k)}
              className={`flex shrink-0 items-center gap-3 whitespace-nowrap rounded-lg border px-3.5 py-2.5 text-sm transition-colors ${tab === k ? "border-[#22C55E]/50 bg-[#22C55E]/10 text-[#22C55E]" : "border-[#272B29] bg-[#121413] text-slate-400 hover:text-white"}`}>
              <Icon size={16} />{l}
              {pending[k] > 0 && <span data-testid={`admin-tab-count-${k}`} className="ml-auto rounded-full bg-[#FFB800] px-2 py-0.5 font-mono text-[10px] font-bold text-black">{pending[k]}</span>}
            </button>
          ))}
        </aside>
        <section className="min-w-0 nk-rise" key={tab}>
          {tab === "overview" && <AdminOverview stats={stats} go={setTab} />}
          {tab === "deposits" && <AdminDeposits onChange={reloadStats} />}
          {tab === "withdrawals" && <AdminWithdrawals onChange={reloadStats} />}
          {tab === "vendors" && <AdminVendors onChange={reloadStats} globalPct={settings?.commission_pct} />}
          {tab === "listings" && <AdminListings onChange={reloadStats} />}
          {tab === "settings" && <AdminSettings settings={settings} onSaved={reloadSettings} />}
          {tab === "site" && <AdminSite />}
          {tab === "users" && <AdminUsers />}
          {tab === "audit" && <AdminAudit />}
        </section>
      </div>
    </div>
  );
}
