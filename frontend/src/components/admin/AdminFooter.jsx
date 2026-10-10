import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Trash2, ArrowLeft, ArrowRight } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { reloadSite } from "@/lib/site";

function Column({ c, i, n, onChange, onMove, onDelete }) {
  const links = c.links;
  const setLink = (j, k, v) => onChange({ ...c, links: links.map((l, x) => (x === j ? { ...l, [k]: v } : l)) });
  return (
    <div className="nk-card space-y-3 p-4" data-testid={`footer-edit-col-${i}`}>
      <div className="flex gap-2">
        <input data-testid={`footer-col-title-${i}`} className="nk-input" placeholder="Column title" value={c.title} onChange={(e) => onChange({ ...c, title: e.target.value })} />
        <button type="button" data-testid={`footer-col-left-${i}`} disabled={i === 0} onClick={() => onMove(-1)} className="nk-btn-ghost h-10 w-10 shrink-0 !p-0"><ArrowLeft size={13} /></button>
        <button type="button" data-testid={`footer-col-right-${i}`} disabled={i === n - 1} onClick={() => onMove(1)} className="nk-btn-ghost h-10 w-10 shrink-0 !p-0"><ArrowRight size={13} /></button>
        <button type="button" data-testid={`footer-col-delete-${i}`} onClick={onDelete} className="nk-btn-ghost h-10 w-10 shrink-0 !p-0 text-[#FF2A5F]"><Trash2 size={14} /></button>
      </div>
      {links.map((l, j) => (
        <div key={j} className="flex gap-2" data-testid={`footer-link-${i}-${j}`}>
          <input data-testid={`footer-link-label-${i}-${j}`} className="nk-input" placeholder="Label" value={l.label} onChange={(e) => setLink(j, "label", e.target.value)} />
          <input data-testid={`footer-link-url-${i}-${j}`} className="nk-input font-mono text-xs" placeholder="/page or https://…" value={l.url} onChange={(e) => setLink(j, "url", e.target.value)} />
          <button type="button" data-testid={`footer-link-delete-${i}-${j}`} onClick={() => onChange({ ...c, links: links.filter((_, x) => x !== j) })} className="nk-btn-ghost h-10 w-10 shrink-0 !p-0 text-[#FF2A5F]"><Trash2 size={13} /></button>
        </div>
      ))}
      {links.length < 10 && <button type="button" data-testid={`footer-link-add-${i}`} onClick={() => onChange({ ...c, links: [...links, { label: "", url: "/" }] })} className="nk-btn-ghost nk-btn-sm"><Plus size={13} />Add link</button>}
    </div>
  );
}

export function AdminFooter() {
  const [f, setF] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.get("/admin/site").then((r) => setF(r.data.footer)); }, []);
  if (!f) return <div className="nk-card h-64 animate-pulse" />;
  const cols = f.columns;
  const setCols = (columns) => setF({ ...f, columns });
  const move = (i, d) => { const l = [...cols]; [l[i], l[i + d]] = [l[i + d], l[i]]; setCols(l); };
  const save = async () => {
    const clean = { ...f, columns: cols.map((c) => ({ ...c, links: c.links.filter((l) => l.label.trim() && l.url.trim()) })) };
    setBusy(true);
    try { const { data } = await api.put("/admin/site", { footer: clean }); setF(data.footer); await reloadSite(); toast.success("Footer saved"); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <div className="space-y-4" data-testid="admin-footer">
      <div><label className="nk-label">Bottom line text</label><input data-testid="footer-text-input" className="nk-input" value={f.text} onChange={(e) => setF({ ...f, text: e.target.value })} /></div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {cols.map((c, i) => <Column key={i} c={c} i={i} n={cols.length} onChange={(v) => setCols(cols.map((x, j) => (j === i ? v : x)))} onMove={(d) => move(i, d)} onDelete={() => setCols(cols.filter((_, j) => j !== i))} />)}
      </div>
      <div className="flex gap-2">
        {cols.length < 6 && <button type="button" data-testid="footer-col-add" onClick={() => setCols([...cols, { title: "New column", links: [] }])} className="nk-btn-ghost nk-btn-sm"><Plus size={13} />Add column</button>}
        <button type="button" data-testid="footer-save" disabled={busy} onClick={save} className="nk-btn-primary nk-btn-sm ml-auto">Save footer</button>
      </div>
    </div>
  );
}
