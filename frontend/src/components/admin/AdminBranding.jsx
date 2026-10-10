import { useEffect, useState } from "react";
import { toast } from "sonner";
import { RotateCcw, Check } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { reloadSite } from "@/lib/site";
import { applyTheme, PRESETS, THEME_KEYS } from "@/lib/theme";
import { ICONS, CategoryIcon } from "@/components/CategoryIcon";

const HEX = /^#[0-9a-f]{6}$/i;

function ColorRow({ k, label, hint, value, onChange }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-line bg-deep px-3 py-2" data-testid={`theme-row-${k}`}>
      <input type="color" data-testid={`theme-color-${k}`} value={HEX.test(value) ? value : "#000000"} onChange={(e) => onChange(e.target.value.toUpperCase())}
        className="h-9 w-9 shrink-0 cursor-pointer rounded-md border border-line bg-transparent p-0.5" />
      <div className="min-w-0 flex-1"><div className="text-sm text-slate-100">{label}</div><div className="truncate text-[11px] text-slate-500">{hint}</div></div>
      <input data-testid={`theme-hex-${k}`} className={`nk-input w-24 font-mono text-xs uppercase ${HEX.test(value) ? "" : "border-[#FF2A5F]"}`} value={value} maxLength={7} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function ThemeEditor({ initial }) {
  const [t, setT] = useState(initial);
  const [busy, setBusy] = useState(false);
  const valid = THEME_KEYS.every(([k]) => HEX.test(t[k]));
  useEffect(() => { if (valid) applyTheme(t, false); }, [t, valid]);
  useEffect(() => () => applyTheme(JSON.parse(localStorage.getItem("nk_theme") || "null") || initial, false), [initial]);
  const save = async () => {
    setBusy(true);
    try { await api.put("/admin/site", { theme: t }); applyTheme(t); await reloadSite(); toast.success("Colors saved for the whole store"); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  const match = Object.entries(PRESETS).find(([, p]) => THEME_KEYS.every(([k]) => p[k].toLowerCase() === t[k].toLowerCase()))?.[0];
  return (
    <div className="nk-card space-y-4 p-5" data-testid="admin-theme-editor">
      <div><h3 className="font-display text-base">Store colors</h3><p className="text-xs text-slate-500">Pick a ready theme or set each color. Changes preview live; press Save to apply for everyone.</p></div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4" data-testid="theme-presets">
        {Object.entries(PRESETS).map(([name, p]) => (
          <button key={name} type="button" data-testid={`theme-preset-${name.toLowerCase().replace(/ /g, "-")}`} onClick={() => setT(p)}
            className={`flex items-center gap-2 rounded-lg border px-2.5 py-2 text-left text-xs ${match === name ? "border-brand/60 bg-brand/10 text-slate-100" : "border-line text-slate-400 hover:text-white"}`}>
            <span className="flex shrink-0 overflow-hidden rounded-md border border-white/10">
              {[p.brand, p.info, p.panel].map((c) => <span key={c} className="h-6 w-3" style={{ background: c }} />)}
            </span>
            <span className="truncate">{name}</span>{match === name && <Check size={12} className="ml-auto shrink-0 text-brand" />}
          </button>
        ))}
      </div>
      <div className="grid gap-2 md:grid-cols-2">{THEME_KEYS.map(([k, l, h]) => <ColorRow key={k} k={k} label={l} hint={h} value={t[k]} onChange={(v) => setT({ ...t, [k]: v })} />)}</div>
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-line bg-ink p-4" data-testid="theme-preview">
        <button type="button" className="nk-btn-primary nk-btn-sm">Primary button</button>
        <button type="button" className="nk-btn-buy nk-btn-sm">Buy</button>
        <span className="font-mono text-sm text-brandlt">$19.99</span>
        <span className="rounded-md bg-info/15 px-2 py-0.5 font-mono text-[11px] text-info">ACCENT</span>
        <span className="nk-card px-3 py-2 text-xs text-slate-300">Card</span>
      </div>
      <div className="flex gap-2">
        <button type="button" data-testid="theme-reset" onClick={() => setT(initial)} className="nk-btn-ghost nk-btn-sm"><RotateCcw size={13} />Undo changes</button>
        <button type="button" data-testid="theme-save" disabled={busy || !valid} onClick={save} className="nk-btn-primary nk-btn-sm ml-auto">Save colors</button>
      </div>
    </div>
  );
}

function BrandEditor({ initial }) {
  const [b, setB] = useState(initial);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setB({ ...b, [k]: e.target.value });
  const save = async () => {
    setBusy(true);
    try { await api.put("/admin/site", { brand: b }); await reloadSite(); toast.success("Store name saved"); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <div className="nk-card space-y-4 p-5" data-testid="admin-brand-editor">
      <div><h3 className="font-display text-base">Store name & logo</h3><p className="text-xs text-slate-500">Shown in the header, footer, login pages and browser tab.</p></div>
      <div className="flex items-center gap-3 rounded-xl border border-line bg-ink p-4" data-testid="brand-preview">
        <span className="grid h-10 w-10 place-items-center rounded-lg bg-brand/10 text-brand"><CategoryIcon name={b.icon} size={20} /></span>
        <span className="font-display text-2xl tracking-tight">{b.name_start}<span className="text-brand">{b.name_end}</span></span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div><label className="nk-label">Name, first part (white)</label><input data-testid="brand-name-start" className="nk-input" value={b.name_start} onChange={set("name_start")} /></div>
        <div><label className="nk-label">Name, second part (colored)</label><input data-testid="brand-name-end" className="nk-input" value={b.name_end} onChange={set("name_end")} /></div>
        <div><label className="nk-label">Browser tab title</label><input data-testid="brand-page-title" className="nk-input" value={b.page_title} onChange={set("page_title")} /></div>
        <div><label className="nk-label">Your store name on admin listings</label><input data-testid="brand-official-store" className="nk-input" value={b.official_store} onChange={set("official_store")} /></div>
      </div>
      <div><label className="nk-label">Logo icon</label>
        <div className="flex flex-wrap gap-1.5">{Object.keys(ICONS).map((k) => (
          <button key={k} type="button" data-testid={`brand-icon-${k}`} onClick={() => setB({ ...b, icon: k })}
            className={`grid h-9 w-9 place-items-center rounded-lg border ${b.icon === k ? "border-brand/60 bg-brand/15 text-brand" : "border-line text-slate-400 hover:text-white"}`}><CategoryIcon name={k} size={16} /></button>
        ))}</div>
      </div>
      <p className="text-[11px] text-slate-500">Products you already listed keep their old store name; new listings use the new one.</p>
      <button type="button" data-testid="brand-save" disabled={busy || !(b.name_start + b.name_end).trim() || !b.page_title.trim() || !b.official_store.trim()} onClick={save} className="nk-btn-primary nk-btn-sm">Save name & logo</button>
    </div>
  );
}

export function AdminBranding() {
  const [s, setS] = useState(null);
  useEffect(() => { api.get("/admin/site").then((r) => setS(r.data)); }, []);
  if (!s) return <div className="nk-card h-64 animate-pulse" />;
  return <div className="space-y-6"><BrandEditor initial={s.brand} /><ThemeEditor initial={s.theme} /></div>;
}
