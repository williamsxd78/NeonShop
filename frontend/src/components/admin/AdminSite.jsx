import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ArrowUp, ArrowDown, Trash2, Plus, CalendarClock } from "lucide-react";
import { TONES, NoticeBox } from "@/components/NoticeBox";
import { api, errMsg } from "@/lib/api";
import { reloadSite } from "@/lib/site";
import { Switch } from "@/components/ui/switch";
import { ICONS, CategoryIcon } from "@/components/CategoryIcon";
import { HeroEditor, BannersEditor } from "@/components/admin/AdminHeroBanners";

const toLocal = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};
const toIso = (local) => (local ? new Date(local).toISOString() : null);

function scheduleState(n) {
  const now = Date.now();
  if (!n.enabled) return ["Hidden", "#94A3B8"];
  if (n.starts_at && new Date(n.starts_at).getTime() > now) return ["Scheduled", "#22D3EE"];
  if (n.ends_at && new Date(n.ends_at).getTime() <= now) return ["Expired", "#FF2A5F"];
  return ["Live now", "#4ADE80"];
}

function NoticeEditor({ initial }) {
  const [n, setN] = useState(initial);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setN({ ...n, [k]: e.target.value });
  const [label, color] = scheduleState(n);
  const save = async () => {
    setBusy(true);
    try { const { data } = await api.put("/admin/site", { notice: n }); setN(data.notice); await reloadSite(); toast.success("Notice saved"); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <div className="nk-card space-y-4 p-5" data-testid="admin-notice-editor">
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-display text-base">Shop notice</h3>
        <span data-testid="notice-schedule-state" className="ml-auto rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase" style={{ color, borderColor: `${color}55` }}>{label}</span>
        <label className="flex items-center gap-2 text-xs text-slate-400">Enabled<Switch data-testid="notice-enabled-switch" checked={n.enabled} onCheckedChange={(v) => setN({ ...n, enabled: v })} /></label>
      </div>
      <div className="flex gap-2">{Object.keys(TONES).map((t) => (
        <button key={t} type="button" data-testid={`notice-tone-${t}`} onClick={() => setN({ ...n, tone: t })} title={t}
          className={`h-7 w-7 rounded-full border-2 ${n.tone === t ? "border-white" : "border-transparent"}`} style={{ background: TONES[t].c }} />
      ))}</div>
      <div><label className="nk-label">Title</label><input data-testid="notice-title-input" className="nk-input" maxLength={80} value={n.title} onChange={set("title")} /></div>
      <div><label className="nk-label">Message</label><textarea data-testid="notice-body-input" className="nk-input min-h-[80px]" maxLength={600} value={n.body} onChange={set("body")} /></div>
      <div><label className="nk-label">Highlight line (green, optional)</label><input data-testid="notice-highlight-input" className="nk-input" maxLength={200} value={n.highlight} onChange={set("highlight")} /></div>
      <div className="rounded-xl border border-[#272B29] bg-[#0E100F] p-3">
        <div className="mb-2 flex items-center gap-2 text-xs text-slate-400"><CalendarClock size={14} />Schedule (optional, your local time). Leave empty to show always.</div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div><label className="nk-label">Show from</label><input data-testid="notice-starts-input" type="datetime-local" className="nk-input" value={toLocal(n.starts_at)} onChange={(e) => setN({ ...n, starts_at: toIso(e.target.value) })} /></div>
          <div><label className="nk-label">Hide after</label><input data-testid="notice-ends-input" type="datetime-local" className="nk-input" value={toLocal(n.ends_at)} onChange={(e) => setN({ ...n, ends_at: toIso(e.target.value) })} /></div>
        </div>
        {(n.starts_at || n.ends_at) && <button data-testid="notice-clear-schedule" onClick={() => setN({ ...n, starts_at: null, ends_at: null })} className="mt-2 text-[11px] text-slate-500 underline">Clear schedule</button>}
      </div>
      <div><div className="nk-label">Preview</div><NoticeBox n={n} testId="notice-preview" /></div>
      <button data-testid="notice-save-btn" disabled={busy} onClick={save} className="nk-btn-primary">Save notice</button>
    </div>
  );
}

const fromSite = (s) => s.categories.map((c) => ({ name: c, original: c, ...(s.category_style[c] || { icon: "package", color: "#22C55E" }) }));

function CategoryRow({ c, i, n, upd, move, remove }) {
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-xl border border-[#272B29] bg-[#0E100F] p-2" data-testid={`category-row-${i}`}>
      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg" style={{ background: `${c.color}1F`, color: c.color }}><CategoryIcon name={c.icon} size={16} /></span>
      <input data-testid={`category-name-${i}`} className="nk-input min-w-[140px] flex-1" maxLength={40} value={c.name} onChange={(e) => upd({ name: e.target.value })} />
      <select data-testid={`category-icon-${i}`} className="nk-input w-28" value={c.icon} onChange={(e) => upd({ icon: e.target.value })}>
        {Object.keys(ICONS).map((k) => <option key={k} value={k}>{k}</option>)}
      </select>
      <input data-testid={`category-color-${i}`} type="color" className="h-9 w-10 cursor-pointer rounded-lg border border-[#272B29] bg-transparent" value={c.color} onChange={(e) => upd({ color: e.target.value })} />
      <button type="button" data-testid={`category-up-${i}`} disabled={i === 0} onClick={() => move(-1)} className="nk-btn-ghost nk-btn-sm px-2"><ArrowUp size={14} /></button>
      <button type="button" data-testid={`category-down-${i}`} disabled={i === n - 1} onClick={() => move(1)} className="nk-btn-ghost nk-btn-sm px-2"><ArrowDown size={14} /></button>
      <button type="button" data-testid={`category-remove-${i}`} disabled={n === 1} onClick={remove} className="nk-btn-danger nk-btn-sm px-2"><Trash2 size={14} /></button>
    </div>
  );
}

function CategoryEditor({ initial }) {
  const [list, setList] = useState(fromSite(initial));
  const [add, setAdd] = useState("");
  const [busy, setBusy] = useState(false);
  const move = (i, d) => { const l = [...list]; [l[i], l[i + d]] = [l[i + d], l[i]]; setList(l); };
  const save = async () => {
    setBusy(true);
    try { const { data } = await api.put("/admin/site", { categories: list }); setList(fromSite(data)); await reloadSite(); toast.success("Categories saved"); }
    catch (e) { toast.error(errMsg(e)); const { data } = await api.get("/admin/site"); setList(fromSite(data)); }
    finally { setBusy(false); }
  };
  const addOne = () => { if (add.trim()) { setList([...list, { name: add.trim(), original: null, icon: "package", color: "#22C55E" }]); setAdd(""); } };
  return (
    <div className="nk-card space-y-4 p-5" data-testid="admin-category-editor">
      <div><h3 className="font-display text-base">Shop categories</h3><p className="text-xs text-slate-500">Name, icon and color for each shop tab. Renaming updates existing products. Categories with products can't be removed.</p></div>
      <div className="space-y-2">{list.map((c, i) => (
        <CategoryRow key={i} c={c} i={i} n={list.length} upd={(p) => setList(list.map((x, j) => (j === i ? { ...x, ...p } : x)))} move={(d) => move(i, d)} remove={() => setList(list.filter((_, j) => j !== i))} />
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
  const [count, setCount] = useState(0);
  useEffect(() => {
    api.get("/admin/site").then((r) => setS(r.data));
    api.get("/site").then((r) => setCount(r.data.product_count));
  }, []);
  if (!s) return <div className="nk-card h-40 animate-pulse" />;
  return (
    <div className="grid gap-6 xl:grid-cols-2">
      <HeroEditor initial={s.hero} count={count} />
      <BannersEditor initial={s.banners} />
      <NoticeEditor initial={s.notice} />
      <CategoryEditor initial={s} />
    </div>
  );
}
