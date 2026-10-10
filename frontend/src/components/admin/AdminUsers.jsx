import { useState } from "react";
import { toast } from "sonner";
import { Search } from "lucide-react";
import { api, errMsg, money, fmtDate } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { StatusBadge, FilterTabs } from "@/components/Shared";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

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
              <td className="font-mono text-brandlt">{money(u.balance_cents)}</td>
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

export function AdjustDialog({ user, onClose, onDone }) {
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const mode = user?.mode;
  const close = () => { setAmount(""); setReason(""); onClose(); };
  const submit = async (e) => {
    e.preventDefault();
    const v = parseFloat(amount);
    setBusy(true);
    try {
      await api.post(`/admin/users/${user.id}/adjust`, { amount: mode ? (mode === "debit" ? -1 : 1) * Math.abs(v) : v, reason });
      toast.success(mode === "debit" ? "Balance deducted" : "Wallet updated"); onDone(); close();
    } catch (e2) { toast.error(errMsg(e2)); } finally { setBusy(false); }
  };
  return (
    <Dialog open={!!user} onOpenChange={(o) => !o && close()}>
      <DialogContent className="border-line bg-surface sm:max-w-md" data-testid="user-adjust-dialog">
        <DialogHeader>
          <DialogTitle className="font-display">{mode === "credit" ? "Add balance" : mode === "debit" ? "Deduct balance" : "Adjust wallet"}</DialogTitle>
          <DialogDescription>{user?.email} · current {money(user?.balance_cents || 0)}{!mode && " · positive to credit, negative to debit"}</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <div><label className="nk-label">Amount (USD)</label>
            <input autoFocus required data-testid="user-adjust-amount-input" className="nk-input font-mono" type="number" step="0.01" min={mode ? "0.01" : undefined} value={amount} onChange={(e) => setAmount(e.target.value)} /></div>
          <div><label className="nk-label">Reason (logged in audit)</label>
            <input required data-testid="user-adjust-reason-input" className="nk-input" placeholder="e.g. Deposit not received, added manually" value={reason} onChange={(e) => setReason(e.target.value)} /></div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={close} className="nk-btn-ghost nk-btn-sm" data-testid="user-adjust-cancel">Cancel</button>
            <button disabled={busy} className={mode === "debit" ? "nk-btn-danger nk-btn-sm" : "nk-btn-primary nk-btn-sm"} data-testid="user-adjust-confirm">{mode === "debit" ? "Deduct" : "Apply"}</button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
