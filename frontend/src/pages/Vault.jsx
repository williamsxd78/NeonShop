import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Copy, Eye, EyeOff, KeyRound } from "lucide-react";
import { api, fmtDate } from "@/lib/api";
import { PageHeader, Empty } from "@/components/Shared";

const mask = (k) => (k.length > 8 ? `${"•".repeat(Math.min(k.length - 4, 16))}${k.slice(-4)}` : "••••");

function KeyCard({ o }) {
  const [show, setShow] = useState(false);
  return (
    <div className="nk-card nk-card-hover p-5" data-testid={`vault-key-${o.id}`}>
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <div className="nk-eyebrow mb-1">{o.category}</div>
          <h3 className="font-semibold">{o.product_title}</h3>
          <p className="text-xs text-slate-500">{o.vendor_name} · {fmtDate(o.created_at)}</p>
        </div>
        <KeyRound className="shrink-0 text-[#A855F7]" size={20} />
      </div>
      <div className="flex items-center gap-2 rounded-lg border border-[#272B29] bg-[#0A0B0B] p-3">
        <code data-testid={`vault-key-value-${o.id}`} className="min-w-0 flex-1 break-all text-sm text-[#22C55E]">{show ? o.license_key : mask(o.license_key)}</code>
        <button data-testid={`vault-toggle-${o.id}`} onClick={() => setShow(!show)} className="text-slate-400 hover:text-white">{show ? <EyeOff size={16} /> : <Eye size={16} />}</button>
        <button data-testid={`vault-copy-${o.id}`} onClick={() => { navigator.clipboard.writeText(o.license_key); toast.success("Key copied"); }} className="text-slate-400 hover:text-white"><Copy size={16} /></button>
      </div>
    </div>
  );
}

export default function Vault() {
  const [orders, setOrders] = useState(null);
  useEffect(() => { api.get("/orders").then((r) => setOrders(r.data)); }, []);
  return (
    <div>
      <PageHeader eyebrow="Secure storage" title="Key vault" />
      {orders === null ? <div className="nk-card h-40 animate-pulse" /> : !orders.length ? <Empty testId="vault-empty" text="Your vault is empty. Purchased keys appear here instantly." /> : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="vault-grid">{orders.map((o) => <KeyCard key={o.id} o={o} />)}</div>
      )}
    </div>
  );
}
