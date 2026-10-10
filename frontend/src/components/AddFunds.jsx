import { useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { toast } from "sonner";
import { AlertTriangle, Copy, CheckCircle2 } from "lucide-react";
import { api, errMsg, money } from "@/lib/api";

export function AddFunds({ onDone }) {
  const [coins, setCoins] = useState([]);
  const [coin, setCoin] = useState("");
  const [amount, setAmount] = useState("");
  const [dep, setDep] = useState(null);
  const [txid, setTxid] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.get("/wallet/coins").then((r) => setCoins(r.data)); }, []);
  const sel = coins.find((c) => c.code === coin);

  const create = async () => {
    setBusy(true);
    try { const { data } = await api.post("/wallet/deposits", { coin, amount: parseFloat(amount) }); setDep(data); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  const submit = async () => {
    setBusy(true);
    try {
      await api.post(`/wallet/deposits/${dep.id}/txid`, { txid });
      toast.success("TXID submitted — waiting for network confirmation. Your balance updates automatically once confirmed.");
      setDep(null); setTxid(""); setAmount(""); onDone?.();
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  const copy = (t) => { navigator.clipboard.writeText(t); toast.success("Copied"); };

  return (
    <div className="nk-card p-6" data-testid="add-funds-panel">
      <div className="nk-eyebrow mb-2">Add funds · crypto</div>
      <h2 className="mb-5 text-xl font-bold">Top up your wallet</h2>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="nk-label">Coin / network</label>
          <select data-testid="deposit-coin-select" className="nk-input" value={coin} disabled={!!dep} onChange={(e) => setCoin(e.target.value)}>
            <option value="">Select coin…</option>
            {coins.map((c) => <option key={c.code} value={c.code}>{`${c.label} — ${c.network}`}</option>)}
          </select>
        </div>
        <div>
          <label className="nk-label">Amount (USD)</label>
          <input data-testid="deposit-amount-input" className="nk-input font-mono" type="number" min="1" step="0.01" placeholder="100.00" value={amount} disabled={!!dep} onChange={(e) => setAmount(e.target.value)} />
        </div>
      </div>

      {sel && (
        <div className="mt-6 grid gap-5 sm:grid-cols-[auto_1fr] nk-rise" data-testid="deposit-address-block">
          <div className="mx-auto rounded-xl bg-white p-3"><QRCodeSVG data-testid="deposit-qr" value={sel.address || "-"} size={148} /></div>
          <div className="min-w-0 space-y-3">
            <div>
              <div className="nk-label">{sel.label} address · {sel.network}</div>
              <div className="flex items-center gap-2 rounded-lg border border-line bg-ink p-3">
                <code data-testid="deposit-address" className="min-w-0 flex-1 break-all text-xs text-brand">{sel.address || "Not configured"}</code>
                <button data-testid="copy-address-btn" onClick={() => copy(sel.address)} className="text-slate-400 hover:text-white"><Copy size={15} /></button>
              </div>
            </div>
            <div data-testid="network-warning" className={`flex gap-2 rounded-lg border p-3 text-xs ${coin.startsWith("USDT") ? "border-[#FF2A5F]/40 bg-[#FF2A5F]/10 text-[#FF8FA9]" : "border-[#FFB800]/30 bg-[#FFB800]/10 text-[#FFD772]"}`}>
              <AlertTriangle size={16} className="shrink-0" /><span>{sel.warning}</span>
            </div>
          </div>
        </div>
      )}

      {!dep ? (
        <button data-testid="deposit-continue-btn" disabled={!coin || !(parseFloat(amount) >= 1) || busy} onClick={create} className="nk-btn-primary mt-6 w-full">I'll send this — generate reference</button>
      ) : (
        <div className="mt-6 space-y-4 rounded-xl border border-brand/30 bg-brand/5 p-4 nk-rise" data-testid="deposit-reference-block">
          <div className="flex flex-wrap items-center justify-between gap-2 font-mono text-sm">
            <span className="flex items-center gap-2 text-brandlt"><CheckCircle2 size={16} />Reference <b data-testid="deposit-reference">{dep.reference}</b></span>
            <span>Expected: <b className="text-brand">{money(dep.amount_cents)}</b> in {sel?.label}</span>
          </div>
          <div>
            <label className="nk-label">Transaction ID (TXID / hash)</label>
            <input data-testid="deposit-txid-input" className="nk-input font-mono" placeholder="Paste the transaction hash after sending" value={txid} onChange={(e) => setTxid(e.target.value)} />
          </div>
          <div className="flex gap-2">
            <button data-testid="deposit-cancel-btn" onClick={() => setDep(null)} className="nk-btn-ghost">Back</button>
            <button data-testid="deposit-submit-txid-btn" disabled={txid.trim().length < 8 || busy} onClick={submit} className="nk-btn-primary flex-1">Submit for verification</button>
          </div>
        </div>
      )}
    </div>
  );
}
