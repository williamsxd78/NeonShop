import { useState } from "react";
import { toast } from "sonner";
import { Search } from "lucide-react";
import { api, errMsg, money, fmtDate } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { StatusBadge, FilterTabs, PromptDialog } from "@/components/Shared";

export function AdminUsers() {
  const [role, setRole] = useState("all");
  const [q, setQ] = useState("");
  const [list, reload] = useFetch("/admin/users", { role, q });
  const [adjust, setAdjust] = useState(null);
  const toggle = async (u) => {
    try { await api.post(`/admin/users/${u.id}/status`, { status: u.status === "suspended" ? "active" : "suspended" }); reload(); }
    catch (e) { toast.error(errMsg(e)); }
  };

  return (
    <div>
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input data-testid="admin-users-search" className="nk-input pl-9" placeholder="Search email or name" value={q} onChange={(e) => setQ(e.target.value)} /></div>
      </div>
      <FilterTabs value={role} onChange={setRole} options={["all", "buyer", "vendor", "admin"]} testPrefix="users-filter" />
      <div className="nk-card overflow-x-auto">
        <table className="nk-table" data-testid="admin-users-table">
          <thead><tr><th>User</th><th>Role</th><th>Wallet</th><th>Earnings</th><th>Joined</th><th>Status</th><th /></tr></thead>
          <tbody>{(list || []).map((u) => (
            <tr key={u.id} data-testid={`admin-user-row-${u.id}`}>
              <td><div className="font-medium text-slate-100">{u.name}</div><div className="text-xs text-slate-500">{u.email}</div></td>
              <td className="font-mono text-xs uppercase">{u.role}</td>
              <td className="font-mono text-[#4ADE80]">{money(u.balance_cents)}</td>
              <td className="font-mono">{u.role === "vendor" ? money(u.earnings_cents) : "-"}</td>
              <td className="font-mono text-xs">{fmtDate(u.created_at)}</td>
              <td><StatusBadge status={u.status} /></td>
              <td className="whitespace-nowrap text-right">
                <button data-testid={`user-adjust-${u.id}`} onClick={() => setAdjust(u)} className="nk-btn-ghost nk-btn-sm mr-2">Credit / debit</button>
                {u.role !== "admin" && <button data-testid={`user-status-${u.id}`} onClick={() => toggle(u)} className={u.status === "suspended" ? "nk-btn-primary nk-btn-sm" : "nk-btn-danger nk-btn-sm"}>{u.status === "suspended" ? "Activate" : "Suspend"}</button>}
              </td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      <AdjustDialog user={adjust} onClose={() => setAdjust(null)} onDone={reload} />
    </div>
  );
}

function AdjustDialog({ user, onClose, onDone }) {
  const [amount, setAmount] = useState(null);
  return (
    <>
      <PromptDialog testId="user-adjust-amount" open={!!user && amount === null} onOpenChange={(o) => !o && onClose()} title={`Adjust wallet · ${user?.email || ""}`}
        description="Use a positive number to credit (e.g. dispute resolution) or negative to debit." label="Amount (USD)" type="number" confirmText="Next"
        onSubmit={async (v) => setAmount(v)} />
      <PromptDialog testId="user-adjust-reason" open={!!user && amount !== null} onOpenChange={(o) => { if (!o) { setAmount(null); onClose(); } }} title="Reason for adjustment" label="Reason (logged in audit)" confirmText="Apply"
        onSubmit={async (r) => {
          try { await api.post(`/admin/users/${user.id}/adjust`, { amount: parseFloat(amount), reason: r }); toast.success("Wallet adjusted"); onDone(); }
          catch (e) { toast.error(errMsg(e)); } finally { setAmount(null); onClose(); }
        }} />
    </>
  );
}
