import { useState } from "react";
import { toast } from "sonner";
import { Copy, Eye, EyeOff, KeyRound, Package } from "lucide-react";
import { fmtDate } from "@/lib/api";

const mask = (k) => (k.length > 8 ? `${"•".repeat(Math.min(k.length - 4, 16))}${k.slice(-4)}` : "••••");
const copy = (t) => { navigator.clipboard.writeText(t); toast.success("Copied"); };

export function DeliveryView({ o }) {
  const [show, setShow] = useState(false);
  return (
    <div className="space-y-3">
      {o.license_key && (
        <div>
          <div className="nk-label">License key</div>
          <div className="flex items-center gap-2 rounded-lg border border-[#272B29] bg-[#0A0B0B] p-3">
            <code data-testid={`vault-key-value-${o.id}`} className="min-w-0 flex-1 break-all text-sm text-[#4ADE80]">{show ? o.license_key : mask(o.license_key)}</code>
            <button data-testid={`vault-toggle-${o.id}`} onClick={() => setShow(!show)} className="text-slate-400 hover:text-white">{show ? <EyeOff size={16} /> : <Eye size={16} />}</button>
            <button data-testid={`vault-copy-${o.id}`} onClick={() => copy(o.license_key)} className="text-slate-400 hover:text-white"><Copy size={16} /></button>
          </div>
        </div>
      )}
      {o.delivery_content && (
        <div>
          <div className="nk-label flex items-center justify-between">{o.license_key ? "Vendor instructions" : "Your digital goods"}
            <button data-testid={`vault-copy-content-${o.id}`} onClick={() => copy(o.delivery_content)} className="text-slate-400 hover:text-white"><Copy size={13} /></button></div>
          <pre data-testid={`delivery-content-${o.id}`} className="max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-[#A855F7]/25 bg-[#A855F7]/[0.06] p-3 font-mono text-xs text-slate-200">{o.delivery_content}</pre>
        </div>
      )}
    </div>
  );
}

export function KeyCard({ o }) {
  const Icon = o.license_key ? KeyRound : Package;
  return (
    <div className="nk-card nk-card-hover p-5" data-testid={`vault-key-${o.id}`}>
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <div className="nk-eyebrow mb-1">{o.category}</div>
          <h3 className="font-semibold">{o.product_title}</h3>
          <p className="text-xs text-slate-500">{o.vendor_name} · {fmtDate(o.created_at)}</p>
        </div>
        <Icon className="shrink-0 text-[#A855F7]" size={20} />
      </div>
      <DeliveryView o={o} />
    </div>
  );
}
