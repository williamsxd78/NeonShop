import { useEffect, useState } from "react";
import { toast } from "sonner";
import { QRCodeSVG } from "qrcode.react";
import { api, errMsg, COIN_LABEL } from "@/lib/api";

export function AdminSettings({ settings, onSaved }) {
  const [pct, setPct] = useState("");
  const [addr, setAddr] = useState({});
  useEffect(() => { if (settings) { setPct(String(settings.commission_pct)); setAddr(settings.addresses); } }, [settings]);

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
    </div>
  );
}
