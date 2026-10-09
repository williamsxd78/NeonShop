import { useState } from "react";
import { toast } from "sonner";
import { api, errMsg, COIN_LABEL } from "@/lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";

const blank = { email: "", amount: "", coin: "OTHER", txid: "", note: "" };

export function ManualDeposit({ open, onOpenChange, onDone }) {
  const [f, setF] = useState(blank);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.post("/admin/deposits/manual", { ...f, amount: parseFloat(f.amount), txid: f.txid || null });
      toast.success(`Credited ${f.email} (ref ${data.reference})`);
      setF(blank); onOpenChange(false); onDone();
    } catch (e2) { toast.error(errMsg(e2)); } finally { setBusy(false); }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-[#272B29] bg-[#121413] sm:max-w-md" data-testid="manual-deposit-dialog">
        <DialogHeader>
          <DialogTitle className="font-display">Add funds manually</DialogTitle>
          <DialogDescription>For payments received outside the normal request flow. The user's wallet is credited instantly and they get a notification and email.</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-3">
          <div><label className="nk-label">User email</label><input data-testid="manual-dep-email" type="email" required className="nk-input" value={f.email} onChange={set("email")} /></div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="nk-label">Amount (USD)</label><input data-testid="manual-dep-amount" type="number" min="0.01" step="0.01" required className="nk-input font-mono" value={f.amount} onChange={set("amount")} /></div>
            <div><label className="nk-label">Paid with</label>
              <select data-testid="manual-dep-coin" className="nk-input" value={f.coin} onChange={set("coin")}>
                {[...Object.keys(COIN_LABEL), "OTHER"].map((c) => <option key={c} value={c}>{COIN_LABEL[c] || "Other / cash"}</option>)}
              </select></div>
          </div>
          <div><label className="nk-label">TXID (optional, blocked if already used)</label><input data-testid="manual-dep-txid" className="nk-input font-mono text-xs" value={f.txid} onChange={set("txid")} /></div>
          <div><label className="nk-label">Note (logged in audit)</label><input data-testid="manual-dep-note" required minLength={2} className="nk-input" placeholder="e.g. User contacted support, payment verified" value={f.note} onChange={set("note")} /></div>
          <button data-testid="manual-dep-submit" disabled={busy} className="nk-btn-primary w-full">{busy ? "Crediting…" : "Credit wallet"}</button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
