import { Loader2, CheckCircle2, AlertTriangle, Search } from "lucide-react";

const LABEL = {
  searching: "Looking for your transaction on the network…",
  checking: "Checking the network…",
  confirming: "Waiting for network confirmations",
  credited: "Confirmed on-chain · auto-credited",
  mismatch: "Needs manual review",
  failed: "Needs manual review",
  not_found: "Needs manual review",
};

export function ChainStatus({ d, testId }) {
  const c = d.chain;
  if (!c?.state || (d.status !== "pending" && c.state !== "credited")) return null;
  const bad = ["mismatch", "failed", "not_found"].includes(c.state);
  const ok = c.state === "credited";
  const Icon = ok ? CheckCircle2 : bad ? AlertTriangle : c.state === "searching" ? Search : Loader2;
  const color = ok ? "text-brandlt" : bad ? "text-[#FFB800]" : "text-info";
  const pct = c.required ? Math.min(100, ((c.confirmations || 0) / c.required) * 100) : 0;
  return (
    <div data-testid={testId} className={`mt-2 space-y-1 text-xs ${color}`}>
      <div className="flex items-center gap-1.5">
        <Icon size={13} className={!ok && !bad ? "animate-spin [animation-duration:2.5s]" : ""} />
        <span>{LABEL[c.state] || c.state}</span>
        {c.state === "confirming" && <span className="font-mono">{c.confirmations}/{c.required}</span>}
      </div>
      {c.state === "confirming" && <div className="h-1 overflow-hidden rounded-full bg-line"><div className="h-full bg-info transition-[width] duration-700" style={{ width: `${pct}%` }} /></div>}
      {c.received && <div className="font-mono text-slate-500">received {c.received} {d.coin.replace("_", " ")}{c.usd_price && ` @ $${Number(c.usd_price).toLocaleString()}`}</div>}
      {c.error && <div className="text-slate-500">{c.error}</div>}
    </div>
  );
}
