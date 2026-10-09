import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ArrowUp, ArrowDown, Trash2, Plus, AlertCircle } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { reloadSite } from "@/lib/site";
import { Switch } from "@/components/ui/switch";

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

function NoticeEditor({ initial }) {
  const [n, setN] = useState(initial);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setN({ ...n, [k]: e.target.value });
  const save = async () => {
    setBusy(true);
    try { await api.put("/admin/site", { notice: n }); await reloadSite(); toast.success("Notice saved"); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <div className="nk-card space-y-4 p-5" data-testid="admin-notice-editor">
      <div className="flex items-center justify-between">
        <h3 className="font-display text-base">Shop notice</h3>
        <label className="flex items-center gap-2 text-xs text-slate-400">Show on shop<Switch data-testid="notice-enabled-switch" checked={n.enabled} onCheckedChange={(v) => setN({ ...n, enabled: v })} /></label>
      </div>
      <div className="flex gap-2">{Object.keys(TONES).map((t) => (
        <button key={t} type="button" data-testid={`notice-tone-${t}`} onClick={() => setN({ ...n, tone: t })} title={t}
          className={`h-7 w-7 rounded-full border-2 ${n.tone === t ? "border-white" : "border-transparent"}`} style={{ background: TONES[t].c }} />
      ))}</div>
      <div><label className="nk-label">Title</label><input data-testid="notice-title-input" className="nk-input" maxLength={80} value={n.title} onChange={set("title")} /></div>
      <div><label className="nk-label">Message</label><textarea data-testid="notice-body-input" className="nk-input min-h-[80px]" maxLength={600} value={n.body} onChange={set("body")} /></div>
      <div><label className="nk-label">Highlight line (green, optional)</label><input data-testid="notice-highlight-input" className="nk-input" maxLength={200} value={n.highlight} onChange={set("highlight")} /></div>
      <div><div className="nk-label">Preview</div>{n.enabled ? <NoticeBox n={n} testId="notice-preview" /> : <p className="text-xs text-slate-500">Hidden from the shop.</p>}</div>
      <button data-testid="notice-save-btn" disabled={busy} onClick={save} className="nk-btn-primary">Save notice</button>
    </div>
  );
}

function CategoryEditor({ initial }) {
  const [list, setList] = useState(initial.map((c) => ({ name: c, original: c })));
  const [add, setAdd] = useState("");
  const [busy, setBusy] = useState(false);
  const move = (i, d) => { const l = [...list]; [l[i], l[i + d]] = [l[i + d], l[i]]; setList(l); };
  const save = async () => {
    setBusy(true);
    try {
      const s = await api.put("/admin/site", { categories: list });
      setList(s.data.categories.map((c) => ({ name: c, original: c })));
      await reloadSite(); toast.success("Categories saved");
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  const addOne = () => { if (add.trim()) { setList([...list, { name: add.trim(), original: null }]); setAdd(""); } };
  return (
    <div className="nk-card space-y-4 p-5" data-testid="admin-category-editor">
      <div><h3 className="font-display text-base">Shop categories</h3><p className="text-xs text-slate-500">Shown as tabs on the shop and in vendor product forms. Renaming updates existing products. Categories with products can't be removed.</p></div>
      <div className="space-y-2">{list.map((c, i) => (
        <div key={i} className="flex items-center gap-2" data-testid={`category-row-${i}`}>
          <input data-testid={`category-name-${i}`} className="nk-input" maxLength={40} value={c.name} onChange={(e) => setList(list.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))} />
          <button type="button" data-testid={`category-up-${i}`} disabled={i === 0} onClick={() => move(i, -1)} className="nk-btn-ghost nk-btn-sm px-2"><ArrowUp size={14} /></button>
          <button type="button" data-testid={`category-down-${i}`} disabled={i === list.length - 1} onClick={() => move(i, 1)} className="nk-btn-ghost nk-btn-sm px-2"><ArrowDown size={14} /></button>
          <button type="button" data-testid={`category-remove-${i}`} disabled={list.length === 1} onClick={() => setList(list.filter((_, j) => j !== i))} className="nk-btn-danger nk-btn-sm px-2"><Trash2 size={14} /></button>
        </div>
      ))}</div>
      <div className="flex gap-2">
        <input data-testid="category-add-input" className="nk-input" maxLength={40} placeholder="New category name" value={add} onChange={(e) => setAdd(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addOne()} />
        <button type="button" data-testid="category-add-btn" onClick={addOne} className="nk-btn-ghost"><Plus size={15} />Add</button>
      </div>
      <button data-testid="category-save-btn" disabled={busy} onClick={save} className="nk-btn-primary">Save categories</button>
    </div>
  );
}

export function AdminSite() {
  const [s, setS] = useState(null);
  useEffect(() => { api.get("/site").then((r) => setS(r.data)); }, []);
  if (!s) return <div className="nk-card h-40 animate-pulse" />;
  return <div className="grid gap-6 xl:grid-cols-2"><NoticeEditor initial={s.notice} /><CategoryEditor initial={s.categories} /></div>;
}
