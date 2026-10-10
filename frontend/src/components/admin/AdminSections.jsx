import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ArrowUp, ArrowDown, Trash2, Plus, ChevronDown, Type, Columns3, Lock } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { reloadSite } from "@/lib/site";
import { Switch } from "@/components/ui/switch";
import { ImagePick } from "@/components/admin/AdminHeroBanners";
import { ICONS, CategoryIcon } from "@/components/CategoryIcon";

const BUILTIN = { hero: "Marketplace header", banners: "Promo banners", notice: "Shop notice", vendors: "Featured vendors", products: "Products (search, tabs, grid)" };
const blank = (type) => ({ id: null, type, enabled: true, title: type === "columns" ? "Why buy from us" : "New section", body: "", image: "", button_text: "", link: "",
  columns: type === "columns" ? [{ icon: "zap", title: "Instant delivery", text: "Keys arrive in seconds." }, { icon: "shield", title: "Verified vendors", text: "Every seller is approved." }, { icon: "card", title: "Crypto wallet", text: "Top up with BTC, USDT, LTC or ETH." }] : [] });

function ColumnsEditor({ cols, onChange, sid }) {
  const upd = (i, k, v) => onChange(cols.map((c, j) => (j === i ? { ...c, [k]: v } : c)));
  return (
    <div className="space-y-2">
      <label className="nk-label">Columns ({cols.length}/6)</label>
      {cols.map((c, i) => (
        <div key={i} className="space-y-2 rounded-lg border border-line bg-surface p-3" data-testid={`sec-${sid}-col-${i}`}>
          <div className="flex gap-2">
            <select data-testid={`sec-${sid}-col-${i}-icon`} className="nk-input w-32" value={c.icon} onChange={(e) => upd(i, "icon", e.target.value)}>{Object.keys(ICONS).map((k) => <option key={k}>{k}</option>)}</select>
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-brand/10 text-brand"><CategoryIcon name={c.icon} size={16} /></span>
            <input data-testid={`sec-${sid}-col-${i}-title`} className="nk-input" placeholder="Column title" value={c.title} onChange={(e) => upd(i, "title", e.target.value)} />
            <button type="button" data-testid={`sec-${sid}-col-${i}-delete`} onClick={() => onChange(cols.filter((_, j) => j !== i))} className="nk-btn-ghost h-10 w-10 shrink-0 !p-0 text-[#FF2A5F]"><Trash2 size={14} /></button>
          </div>
          <textarea data-testid={`sec-${sid}-col-${i}-text`} className="nk-input min-h-[60px]" placeholder="Column text" value={c.text} onChange={(e) => upd(i, "text", e.target.value)} />
        </div>
      ))}
      {cols.length < 6 && <button type="button" data-testid={`sec-${sid}-col-add`} onClick={() => onChange([...cols, { icon: "sparkles", title: "", text: "" }])} className="nk-btn-ghost nk-btn-sm"><Plus size={13} />Add column</button>}
    </div>
  );
}

function SectionRow({ s, i, n, onChange, onMove, onDelete }) {
  const [open, setOpen] = useState(!s.id);
  const custom = !BUILTIN[s.type];
  const set = (k) => (e) => onChange({ ...s, [k]: e.target.value });
  const Icon = s.type === "columns" ? Columns3 : s.type === "text" ? Type : Lock;
  return (
    <div className={`nk-card overflow-hidden ${s.enabled ? "" : "opacity-60"}`} data-testid={`sec-row-${i}`}>
      <div className="flex items-center gap-2 p-3">
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-surface text-slate-400"><Icon size={14} /></span>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm text-slate-100">{custom ? s.title || "Untitled section" : BUILTIN[s.type]}</div>
          <div className="font-mono text-[10px] uppercase text-slate-500">{custom ? (s.type === "columns" ? "Columns section" : "Text & image section") : "Built-in"}</div>
        </div>
        <Switch data-testid={`sec-enabled-${i}`} checked={s.enabled} onCheckedChange={(v) => onChange({ ...s, enabled: v })} />
        <button type="button" data-testid={`sec-up-${i}`} disabled={i === 0} onClick={() => onMove(-1)} className="nk-btn-ghost h-8 w-8 !p-0"><ArrowUp size={13} /></button>
        <button type="button" data-testid={`sec-down-${i}`} disabled={i === n - 1} onClick={() => onMove(1)} className="nk-btn-ghost h-8 w-8 !p-0"><ArrowDown size={13} /></button>
        {custom && <button type="button" data-testid={`sec-edit-${i}`} onClick={() => setOpen(!open)} className="nk-btn-ghost h-8 w-8 !p-0"><ChevronDown size={14} className={open ? "rotate-180" : ""} /></button>}
        {custom && <button type="button" data-testid={`sec-delete-${i}`} onClick={onDelete} className="nk-btn-ghost h-8 w-8 !p-0 text-[#FF2A5F]"><Trash2 size={13} /></button>}
      </div>
      {custom && open && (
        <div className="space-y-3 border-t border-line p-4">
          <div><label className="nk-label">Title</label><input data-testid={`sec-title-${i}`} className="nk-input" value={s.title} onChange={set("title")} /></div>
          <div><label className="nk-label">Text</label><textarea data-testid={`sec-body-${i}`} className="nk-input min-h-[80px]" value={s.body} onChange={set("body")} /></div>
          {s.type === "text" && <div><label className="nk-label">Image (optional)</label><ImagePick testId={`sec-image-${i}`} value={s.image} onChange={(v) => onChange({ ...s, image: v })} /></div>}
          {s.type === "columns" && <ColumnsEditor sid={i} cols={s.columns} onChange={(columns) => onChange({ ...s, columns })} />}
          <div className="grid gap-3 sm:grid-cols-2">
            <div><label className="nk-label">Button text (optional)</label><input data-testid={`sec-btn-${i}`} className="nk-input" value={s.button_text} onChange={set("button_text")} /></div>
            <div><label className="nk-label">Button link (/page or https://…)</label><input data-testid={`sec-link-${i}`} className="nk-input" value={s.link} onChange={set("link")} /></div>
          </div>
        </div>
      )}
    </div>
  );
}

export function AdminSections() {
  const [list, setList] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.get("/admin/site").then((r) => setList(r.data.sections)); }, []);
  if (!list) return <div className="nk-card h-64 animate-pulse" />;
  const move = (i, d) => { const l = [...list]; [l[i], l[i + d]] = [l[i + d], l[i]]; setList(l); };
  const save = async () => {
    setBusy(true);
    try { const { data } = await api.put("/admin/site", { sections: list }); setList(data.sections); await reloadSite(); toast.success("Home page sections saved"); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <div className="space-y-3" data-testid="admin-sections">
      <p className="text-xs text-slate-500">Reorder, show/hide or add sections on the shop home page. Built-in sections can be hidden but not deleted.</p>
      {list.map((s, i) => <SectionRow key={s.id || `new-${i}`} s={s} i={i} n={list.length} onChange={(v) => setList(list.map((x, j) => (j === i ? v : x)))}
        onMove={(d) => move(i, d)} onDelete={() => setList(list.filter((_, j) => j !== i))} />)}
      <div className="flex flex-wrap gap-2 pt-1">
        <button type="button" data-testid="sec-add-text" onClick={() => setList([...list, blank("text")])} className="nk-btn-ghost nk-btn-sm"><Type size={13} />Add text & image section</button>
        <button type="button" data-testid="sec-add-columns" onClick={() => setList([...list, blank("columns")])} className="nk-btn-ghost nk-btn-sm"><Columns3 size={13} />Add columns section</button>
        <button type="button" data-testid="sec-save" disabled={busy} onClick={save} className="nk-btn-primary nk-btn-sm ml-auto">Save sections</button>
      </div>
    </div>
  );
}
