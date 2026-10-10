import { AlertCircle } from "lucide-react";

export const TONES = {
  amber: { c: "#FFB800", bg: "rgba(255,184,0,0.06)", b: "rgba(255,184,0,0.3)" },
  green: { c: "rgb(var(--nk-brandlt))", bg: "rgb(var(--nk-brand)/0.06)", b: "rgb(var(--nk-brand)/0.3)" },
  cyan: { c: "rgb(var(--nk-info))", bg: "rgb(var(--nk-info)/0.06)", b: "rgb(var(--nk-info)/0.3)" },
  red: { c: "#FF2A5F", bg: "rgba(255,42,95,0.06)", b: "rgba(255,42,95,0.3)" },
};

export const NoticeBox = ({ n, testId = "sales-final-notice" }) => {
  const t = TONES[n.tone] || TONES.amber;
  return (
    <div data-testid={testId} className="flex gap-3 rounded-2xl border p-4" style={{ borderColor: t.b, background: t.bg }}>
      <AlertCircle size={18} className="mt-0.5 shrink-0" style={{ color: t.c }} />
      <div className="text-sm">
        {n.title && <div className="font-semibold" style={{ color: t.c }}>{n.title}</div>}
        {n.body && <p className="whitespace-pre-line text-slate-400">{n.body}</p>}
        {n.highlight && <p className="mt-1 text-brandlt">{n.highlight}</p>}
      </div>
    </div>
  );
};
