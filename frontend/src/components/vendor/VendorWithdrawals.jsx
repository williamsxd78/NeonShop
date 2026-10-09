import { useState } from "react";
import { toast } from "sonner";
import { api, errMsg, money, fmtDate, COIN_LABEL } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { StatusBadge, Empty } from "@/components/Shared";

export function VendorWithdrawals({ earnings, onChanged }) {
  const [list, reload] = useFetch("/vendor/withdrawals");
  const [f, setF] = useState({ amount: "", coin: "USDT_TRC20", address: "" });
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/vendor/withdrawals", { ...f, amount: parseFloat(f.amount) });
      toast.success("Withdrawal requested"); setF({ ...f, amount: "" }); reload(); onChanged();
    } catch (e2) { toast.error(errMsg(e2)); } finally { setBusy(false); }
  };
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_1.4fr]">
      <form onSubmit={submit} className="nk-card space-y-4 p-6" data-testid="withdraw-form">
        <div><div className="nk-label">Withdrawable earnings</div><div className="font-mono text-2xl text-[#4ADE80]">{money(earnings)}</div></div>
        <div><label className="nk-label">Amount (USD)</label><input data-testid="withdraw-amount-input" className="nk-input font-mono" type="number" min="1" step="0.01" required value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} /></div>
        <div><label className="nk-label">Payout coin</label>
          <select data-testid="withdraw-coin-select" className="nk-input" value={f.coin} onChange={(e) => setF({ ...f, coin: e.target.value })}>
            {Object.entries(COIN_LABEL).map(([c, l]) => <option key={c} value={c}>{l}</option>)}
          </select></div>
        <div><label className="nk-label">Your receiving address</label><input data-testid="withdraw-address-input" className="nk-input font-mono text-xs" required minLength={10} value={f.address} onChange={(e) => setF({ ...f, address: e.target.value })} /></div>
        <button data-testid="withdraw-submit-btn" disabled={busy} className="nk-btn-primary w-full">Request payout</button>
        <p className="text-xs text-slate-500">Payouts are sent manually by admin. Amount is held from earnings until processed.</p>
      </form>
      <div className="nk-card overflow-x-auto p-6">
        <h3 className="mb-4 font-bold">Payout history</h3>
        {!list?.length ? <Empty text="No withdrawal requests yet." /> : (
          <table className="nk-table" data-testid="withdraw-history">
            <thead><tr><th>Date</th><th>Coin</th><th>Amount</th><th>Status</th></tr></thead>
            <tbody>{list.map((w) => (
              <tr key={w.id}><td className="font-mono text-xs">{fmtDate(w.created_at)}</td><td className="text-xs">{COIN_LABEL[w.coin]}</td>
                <td className="font-mono">{money(w.amount_cents)}</td><td><StatusBadge status={w.status} />{w.reason && <div className="mt-1 text-xs text-[#FF2A5F]">{w.reason}</div>}</td></tr>
            ))}</tbody>
          </table>
        )}
      </div>
    </div>
  );
}
