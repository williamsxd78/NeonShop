import { useEffect, useState } from "react";
import { toast } from "sonner";
import { QRCodeSVG } from "qrcode.react";
import { api, errMsg, COIN_LABEL } from "@/lib/api";

export function AdminSettings({ settings, onSaved }) {
  const [pct, setPct] = useState("");
  const [addr, setAddr] = useState({});
  const [av, setAv] = useState({});
  useEffect(() => { if (settings) { setPct(String(settings.commission_pct)); setAddr(settings.addresses); setAv(settings.auto_verify || {}); } }, [settings]);

  const save = async (body, msg) => {
    try { await api.put("/admin/settings", body); toast.success(msg); onSaved(); } catch (e) { toast.error(errMsg(e)); }
  };
  if (!settings) return null;

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
      <div className="nk-card space-y-4 p-6" data-testid="commission-settings">
        <div className="nk-eyebrow">Platform cut</div>
        <h3 className="text-lg font-bold">Global commission</h3>
        <p className="text-xs text-slate-500">Applied at sale time to every vendor without a custom rate. Per-vendor rates are set in the Vendors tab.</p>
        <div className="flex gap-2">
          <input data-testid="global-commission-input" className="nk-input font-mono" type="number" min="0" max="100" step="0.1" value={pct} onChange={(e) => setPct(e.target.value)} />
          <button data-testid="global-commission-save" onClick={() => save({ commission_pct: parseFloat(pct) }, "Commission updated")} className="nk-btn-primary">Save</button>
        </div>
      </div>
      <div className="nk-card space-y-4 p-6" data-testid="address-settings">
        <div className="nk-eyebrow">Receiving wallets</div>
        <h3 className="text-lg font-bold">Crypto deposit addresses</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          {Object.keys(COIN_LABEL).map((c) => (
            <div key={c} className="flex gap-3 rounded-lg border border-line bg-deep p-3">
              <div className="h-fit rounded bg-white p-1.5"><QRCodeSVG value={addr[c] || "-"} size={56} /></div>
              <div className="min-w-0 flex-1">
                <label className="nk-label">{COIN_LABEL[c]}</label>
                <input data-testid={`address-input-${c}`} className="nk-input font-mono text-xs" value={addr[c] || ""} onChange={(e) => setAddr({ ...addr, [c]: e.target.value })} />
              </div>
            </div>
          ))}
        </div>
        <button data-testid="addresses-save-btn" onClick={() => save({ addresses: addr }, "Addresses saved")} className="nk-btn-primary">Save addresses</button>
      </div>
      <AutoVerify av={av} setAv={setAv} onSave={() => save({ auto_verify: av }, "Auto-verify settings saved")} />
    </div>
  );
}

function AutoVerify({ av, setAv, onSave }) {
  const set = (c, k, v) => setAv({ ...av, [c]: { ...av[c], [k]: v } });
  return (
    <div className="nk-card space-y-4 p-6 lg:col-span-2" data-testid="auto-verify-settings">
      <div className="nk-eyebrow">Blockchain auto-verify</div>
      <h3 className="text-lg font-bold">Automatic deposit confirmation</h3>
      <p className="text-xs text-slate-500">When a buyer submits a TXID, the network is checked every minute. Once the payment to your address reaches the required confirmations, the received amount × live CoinGecko price is credited and the request leaves your pending queue. You can still approve or reject manually at any time, which stops auto-checking for that deposit.</p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {Object.keys(COIN_LABEL).filter((c) => av[c]).map((c) => (
          <div key={c} className="space-y-2 rounded-lg border border-line bg-deep p-3" data-testid={`auto-verify-${c}`}>
            <label className="flex items-center justify-between gap-2 text-sm font-medium">
              {COIN_LABEL[c]}
              <input type="checkbox" data-testid={`auto-verify-toggle-${c}`} className="h-4 w-4 accent-[rgb(var(--nk-brand))]" checked={!!av[c].enabled} onChange={(e) => set(c, "enabled", e.target.checked)} />
            </label>
            <div><span className="nk-label">Confirmations</span>
              <input data-testid={`auto-verify-conf-${c}`} type="number" min="1" max="500" className="nk-input font-mono" value={av[c].confirmations} onChange={(e) => set(c, "confirmations", parseInt(e.target.value, 10) || 1)} /></div>
          </div>
        ))}
      </div>
      <button data-testid="auto-verify-save-btn" onClick={onSave} className="nk-btn-primary">Save auto-verify</button>
    </div>
  );
}
