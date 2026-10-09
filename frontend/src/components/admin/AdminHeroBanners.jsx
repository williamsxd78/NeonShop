import { useState } from "react";
import { toast } from "sonner";
import { Upload, Plus, Trash2, ArrowUp, ArrowDown } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { reloadSite } from "@/lib/site";
import { Switch } from "@/components/ui/switch";
import { ShopHero, BannerCarousel } from "@/components/ShopHero";

export function ImagePick({ value, onChange, testId }) {
  const [busy, setBusy] = useState(false);
  const up = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    setBusy(true);
    try { const { data } = await api.post("/upload", fd); onChange(data.url); toast.success("Image uploaded"); }
    catch (e2) { toast.error(errMsg(e2)); } finally { setBusy(false); }
  };
  return (
    <div className="flex gap-2">
      <input data-testid={`${testId}-url`} className="nk-input text-xs" placeholder="Image URL or upload" value={value} onChange={(e) => onChange(e.target.value)} />
      <label className="nk-btn-ghost nk-btn-sm shrink-0 cursor-pointer"><Upload size={14} />{busy ? "…" : "Upload"}<input data-testid={`${testId}-file`} type="file" accept="image/*" className="hidden" onChange={up} /></label>
    </div>
  );
}

const save = async (body, msg) => {
  try { await api.put("/admin/site", body); await reloadSite(); toast.success(msg); return true; }
  catch (e) { toast.error(errMsg(e)); return false; }
};

export function HeroEditor({ initial, count }) {
  const [h, setH] = useState(initial);
  const set = (k) => (e) => setH({ ...h, [k]: e.target.value });
  return (
    <div className="nk-card space-y-4 p-5" data-testid="admin-hero-editor">
      <div className="flex items-center justify-between">
        <h3 className="font-display text-base">Marketplace header</h3>
        <label className="flex items-center gap-2 text-xs text-slate-400">Show<Switch data-testid="hero-enabled-switch" checked={h.enabled} onCheckedChange={(v) => setH({ ...h, enabled: v })} /></label>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div><label className="nk-label">Title</label><input data-testid="hero-title-input" className="nk-input" maxLength={60} value={h.title} onChange={set("title")} /></div>
        <div><label className="nk-label">Subtitle ({"{count}"} = live product count)</label><input data-testid="hero-subtitle-input" className="nk-input" maxLength={120} value={h.subtitle} onChange={set("subtitle")} /></div>
      </div>
      <div><label className="nk-label">Background image</label><ImagePick testId="hero-image" value={h.image} onChange={(image) => setH({ ...h, image })} /></div>
      <div><div className="nk-label">Preview</div>{h.enabled ? <div className="pointer-events-none overflow-hidden rounded-2xl"><ShopHero hero={h} count={count} /></div> : <p className="text-xs text-slate-500">Hidden from the shop.</p>}</div>
      <button data-testid="hero-save-btn" onClick={() => save({ hero: h }, "Header saved")} className="nk-btn-primary">Save header</button>
    </div>
  );
}

const blankBanner = { enabled: true, title: "", subtitle: "", button_text: "", link: "", image: "" };

export function BannersEditor({ initial }) {
  const [list, setList] = useState(initial);
  const upd = (i, patch) => setList(list.map((b, j) => (j === i ? { ...b, ...patch } : b)));
  const move = (i, d) => { const l = [...list]; [l[i], l[i + d]] = [l[i + d], l[i]]; setList(l); };
  const submit = async () => {
    if (list.some((b) => !b.image)) return toast.error("Every banner needs an image");
    await save({ banners: list }, "Banners saved");
    const { data } = await api.get("/admin/site");
    setList(data.banners);
  };
  return (
    <div className="nk-card space-y-4 p-5" data-testid="admin-banners-editor">
      <div><h3 className="font-display text-base">Promo banners</h3><p className="text-xs text-slate-500">Shown as a sliding carousel at the top of the shop. Links can be internal (/vendors) or external (https://…).</p></div>
      {list.map((b, i) => (
        <div key={b.id || i} className="space-y-3 rounded-xl border border-[#272B29] bg-[#0E100F] p-4" data-testid={`banner-row-${i}`}>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-slate-500">Banner {i + 1}</span>
            <label className="ml-auto flex items-center gap-2 text-xs text-slate-400">Live<Switch data-testid={`banner-enabled-${i}`} checked={b.enabled} onCheckedChange={(v) => upd(i, { enabled: v })} /></label>
            <button data-testid={`banner-up-${i}`} disabled={i === 0} onClick={() => move(i, -1)} className="nk-btn-ghost nk-btn-sm px-2"><ArrowUp size={13} /></button>
            <button data-testid={`banner-down-${i}`} disabled={i === list.length - 1} onClick={() => move(i, 1)} className="nk-btn-ghost nk-btn-sm px-2"><ArrowDown size={13} /></button>
            <button data-testid={`banner-remove-${i}`} onClick={() => setList(list.filter((_, j) => j !== i))} className="nk-btn-danger nk-btn-sm px-2"><Trash2 size={13} /></button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <input data-testid={`banner-title-${i}`} className="nk-input" placeholder="Title" maxLength={80} value={b.title} onChange={(e) => upd(i, { title: e.target.value })} />
            <input data-testid={`banner-subtitle-${i}`} className="nk-input" placeholder="Subtitle" maxLength={200} value={b.subtitle} onChange={(e) => upd(i, { subtitle: e.target.value })} />
            <input data-testid={`banner-button-${i}`} className="nk-input" placeholder="Button text (optional)" maxLength={30} value={b.button_text} onChange={(e) => upd(i, { button_text: e.target.value })} />
            <input data-testid={`banner-link-${i}`} className="nk-input" placeholder="Link: /vendors or https://…" maxLength={500} value={b.link} onChange={(e) => upd(i, { link: e.target.value })} />
          </div>
          <ImagePick testId={`banner-image-${i}`} value={b.image} onChange={(image) => upd(i, { image })} />
          {b.image && <div className="pointer-events-none"><BannerCarousel banners={[{ ...b, id: `p${i}` }]} /></div>}
        </div>
      ))}
      <div className="flex gap-2">
        <button data-testid="banner-add-btn" disabled={list.length >= 12} onClick={() => setList([...list, { ...blankBanner }])} className="nk-btn-ghost"><Plus size={15} />Add banner</button>
        <button data-testid="banners-save-btn" onClick={submit} className="nk-btn-primary">Save banners</button>
      </div>
    </div>
  );
}
