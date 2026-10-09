import { useState } from "react";
import { money, fmtDate } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { FilterTabs, Stat } from "@/components/Shared";

const GROUPS = { all: "", deposits: "deposit", orders: "order", payouts: "withdrawal", pricing: "product.price", commission: "commission", wallet: "wallet" };

export function AdminAudit() {
  const [g, setG] = useState("all");
  const [list] = useFetch("/admin/audit", { action: GROUPS[g] });
  return (
    <div>
      <FilterTabs value={g} onChange={setG} options={Object.keys(GROUPS)} testPrefix="audit-filter" />
      <div className="nk-card overflow-x-auto">
        <table className="nk-table" data-testid="admin-audit-table">
          <thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Details</th><th className="text-right">Amount</th></tr></thead>
          <tbody>{(list || []).map((a) => (
            <tr key={a.id}>
              <td className="whitespace-nowrap font-mono text-xs">{fmtDate(a.created_at)}</td>
              <td className="text-xs">{a.actor_email}</td>
              <td className="font-mono text-xs text-[#A855F7]">{a.action}</td>
              <td className="max-w-md text-xs">{a.details}</td>
              <td className={`text-right font-mono text-xs ${a.amount_cents == null ? "text-slate-600" : a.amount_cents >= 0 ? "text-[#4ADE80]" : "text-[#FF2A5F]"}`}>{a.amount_cents == null ? "-" : money(a.amount_cents)}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}

export function AdminOverview({ stats, go }) {
  if (!stats) return null;
  const q = [["deposits", "Deposits to verify"], ["withdrawals", "Payouts to send"], ["vendors", "Vendors to approve"], ["listings", "Listings to review"]];
  return (
    <div className="space-y-6" data-testid="admin-overview">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {q.map(([k, l]) => (
          <button key={k} data-testid={`overview-queue-${k}`} onClick={() => go(k)} className="nk-card nk-card-hover p-5 text-left">
            <div className="nk-label">{l}</div>
            <div className={`font-mono text-3xl font-semibold ${stats.pending[k] ? "text-[#FFB800]" : "text-slate-500"}`}>{stats.pending[k]}</div>
          </button>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat testId="astat-volume" label="Sales volume" value={money(stats.volume_cents)} />
        <Stat testId="astat-commission" label="Platform revenue" value={money(stats.commission_cents)} accent="#4ADE80" />
        <Stat testId="astat-deposits" label="Deposits credited" value={money(stats.deposits_cents)} accent="#A855F7" />
        <Stat testId="astat-orders" label="Orders" value={stats.orders} />
        <Stat label="Buyers" value={stats.users} />
        <Stat label="Active vendors" value={stats.vendors} />
        <Stat label="Live products" value={stats.products_live} />
      </div>
      <div className="nk-card overflow-x-auto p-6">
        <h3 className="mb-4 font-bold">Recent orders</h3>
        <table className="nk-table">
          <thead><tr><th>Time</th><th>Product</th><th>Buyer</th><th>Vendor</th><th>Price</th><th className="text-right">Commission</th></tr></thead>
          <tbody>{stats.recent_orders.map((o) => (
            <tr key={o.id}><td className="font-mono text-xs">{fmtDate(o.created_at)}</td><td>{o.product_title}</td><td className="text-xs">{o.buyer_email}</td>
              <td className="text-xs">{o.vendor_name}</td><td className="font-mono">{money(o.price_cents)}</td><td className="text-right font-mono text-[#4ADE80]">{money(o.commission_cents)}</td></tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}
