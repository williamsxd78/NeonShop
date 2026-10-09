import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";

const STATUS = {
  approved: "text-[#4ADE80] border-[#4ADE80]/30 bg-[#4ADE80]/10",
  paid: "text-[#4ADE80] border-[#4ADE80]/30 bg-[#4ADE80]/10",
  delivered: "text-[#4ADE80] border-[#4ADE80]/30 bg-[#4ADE80]/10",
  active: "text-[#4ADE80] border-[#4ADE80]/30 bg-[#4ADE80]/10",
  available: "text-[#4ADE80] border-[#4ADE80]/30 bg-[#4ADE80]/10",
  pending: "text-[#FFB800] border-[#FFB800]/30 bg-[#FFB800]/10",
  awaiting_txid: "text-[#A855F7] border-[#A855F7]/30 bg-[#A855F7]/10",
  reserved: "text-[#A855F7] border-[#A855F7]/30 bg-[#A855F7]/10",
  rejected: "text-[#FF2A5F] border-[#FF2A5F]/30 bg-[#FF2A5F]/10",
  suspended: "text-[#FF2A5F] border-[#FF2A5F]/30 bg-[#FF2A5F]/10",
  sold: "text-slate-400 border-slate-600/40 bg-slate-700/20",
};

export const StatusBadge = ({ status, testId }) => (
  <span data-testid={testId} className={`inline-flex items-center whitespace-nowrap rounded-full border px-2.5 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider ${STATUS[status] || "text-slate-300 border-slate-600"}`}>
    {String(status || "").replace("_", " ")}
  </span>
);

export const PageHeader = ({ eyebrow, title, children }) => (
  <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between nk-rise">
    <div>
      {eyebrow && <div className="nk-eyebrow mb-2">{eyebrow}</div>}
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
    </div>
    {children}
  </div>
);

export const Stat = ({ label, value, accent = "#22C55E", testId }) => (
  <div className="nk-card p-5" data-testid={testId}>
    <div className="nk-label">{label}</div>
    <div className="font-mono text-xl" style={{ color: accent }}>{value}</div>
  </div>
);

export const Empty = ({ text, testId }) => (
  <div data-testid={testId} className="nk-card grid place-items-center p-12 text-center text-sm text-slate-500">{text}</div>
);

export function PromptDialog({ open, onOpenChange, title, description, label, type = "text", defaultValue = "", confirmText = "Confirm", danger, required = true, onSubmit, testId = "prompt" }) {
  const [val, setVal] = useState(defaultValue);
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try { await onSubmit(val); onOpenChange(false); } finally { setBusy(false); }
  };
  return (
    <Dialog open={open} onOpenChange={(o) => { if (o) setVal(defaultValue); onOpenChange(o); }}>
      <DialogContent className="border-[#272B29] bg-[#121413] sm:max-w-md" data-testid={`${testId}-dialog`}>
        <DialogHeader>
          <DialogTitle className="font-display">{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="nk-label">{label}</label>
            <input autoFocus data-testid={`${testId}-input`} className="nk-input" type={type} step="0.01" required={required} value={val} onChange={(e) => setVal(e.target.value)} />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" className="nk-btn-ghost nk-btn-sm" onClick={() => onOpenChange(false)} data-testid={`${testId}-cancel`}>Cancel</button>
            <button type="submit" disabled={busy} className={danger ? "nk-btn-danger nk-btn-sm" : "nk-btn-primary nk-btn-sm"} data-testid={`${testId}-confirm`}>{confirmText}</button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function ConfirmDialog({ open, onOpenChange, title, description, confirmText = "Delete", onConfirm, testId = "confirm" }) {
  const [busy, setBusy] = useState(false);
  const go = async () => { setBusy(true); try { await onConfirm(); onOpenChange(false); } finally { setBusy(false); } };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-[#272B29] bg-[#121413] sm:max-w-md" data-testid={`${testId}-dialog`}>
        <DialogHeader><DialogTitle className="font-display">{title}</DialogTitle>{description && <DialogDescription>{description}</DialogDescription>}</DialogHeader>
        <div className="flex justify-end gap-2">
          <button className="nk-btn-ghost nk-btn-sm" onClick={() => onOpenChange(false)} data-testid={`${testId}-cancel`}>Cancel</button>
          <button disabled={busy} className="nk-btn-danger nk-btn-sm" onClick={go} data-testid={`${testId}-confirm`}>{confirmText}</button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export const FilterTabs = ({ value, onChange, options, testPrefix }) => (
  <div className="no-scrollbar mb-5 flex gap-2 overflow-x-auto">
    {options.map((o) => (
      <button key={o} data-testid={`${testPrefix}-${o}`} onClick={() => onChange(o)}
        className={`whitespace-nowrap rounded-full border px-3.5 py-1.5 text-xs font-mono uppercase tracking-wider transition-colors ${value === o ? "border-[#22C55E]/60 bg-[#22C55E]/10 text-[#22C55E]" : "border-[#272B29] text-slate-400 hover:text-white"}`}>
        {o.replace("_", " ")}
      </button>
    ))}
  </div>
);
