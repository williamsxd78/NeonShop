import { AlertCircle } from "lucide-react";

export const TONES = {
  amber: { c: "#FFB800", bg: "rgba(255,184,0,0.06)", b: "rgba(255,184,0,0.3)" },
  green: { c: "#4ADE80", bg: "rgba(34,197,94,0.06)", b: "rgba(34,197,94,0.3)" },
  cyan: { c: "#22D3EE", bg: "rgba(34,211,238,0.06)", b: "rgba(34,211,238,0.3)" },
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
        {n.highlight && <p className="mt-1 text-[#4ADE80]">{n.highlight}</p>}
      </div>
    </div>
  );
};
