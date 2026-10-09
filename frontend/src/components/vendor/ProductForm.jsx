import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Upload, Check, X, KeyRound, FileText, Lock, Eye } from "lucide-react";
import { api, errMsg, CATEGORIES, imgSrc } from "@/lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

const DEFAULT_IMAGES = [
  "https://images.unsplash.com/photo-1608742213509-815b97c30b36?w=800&q=80",
  "https://images.unsplash.com/photo-1720962158937-7ea890052166?w=800&q=80",
  "https://images.unsplash.com/photo-1705510144116-cc4d88838b14?w=800&q=80",
  "https://images.unsplash.com/photo-1663811459413-e9de4614f88f?w=800&q=80",
  "https://images.unsplash.com/photo-1645395759348-a0dd7ccf1602?w=800&q=80",
];
const blank = { title: "", description: "", category: CATEGORIES[0], price: "", image: "", tags: [], delivery_type: "keys", delivery_content: "" };

function TagInput({ tags, onChange }) {
  const [t, setT] = useState("");
  const add = () => {
    const v = t.trim().toLowerCase().replace(/,/g, "");
    if (v && !tags.includes(v) && tags.length < 8) onChange([...tags, v]);
    setT("");
  };
  return (
    <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-[#272B29] bg-[#0E100F] p-2">
      {tags.map((x) => (
        <span key={x} className="flex items-center gap-1 rounded-md bg-[#22D3EE]/10 px-2 py-0.5 font-mono text-[11px] uppercase text-[#22D3EE]">
          {x}<button type="button" data-testid={`pf-tag-remove-${x}`} onClick={() => onChange(tags.filter((y) => y !== x))}><X size={11} /></button>
        </span>
      ))}
      <input data-testid="pf-tags-input" className="min-w-[120px] flex-1 bg-transparent px-1 py-1 text-sm outline-none placeholder:text-slate-500" placeholder={tags.length < 8 ? "Type a tag, press Enter" : "Max 8 tags"}
        value={t} onChange={(e) => setT(e.target.value)} onBlur={add}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === ",") { e.preventDefault(); add(); } }} />
    </div>
  );
}

const Section = ({ icon: Icon, title, hint, children, color = "#4ADE80" }) => (
  <div className="space-y-3 rounded-xl border border-[#272B29] bg-[#121413] p-4">
    <div className="flex items-center gap-2"><Icon size={15} style={{ color }} /><span className="font-display text-sm font-semibold">{title}</span>
      {hint && <span className="ml-auto text-[11px] text-slate-500">{hint}</span>}</div>
    {children}
  </div>
);

export function ProductForm({ open, onOpenChange, product, onSaved }) {
  const [f, setF] = useState(blank);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (open) setF(product ? { ...blank, ...product, price: (product.vendor_price_cents ?? product.price_cents) / 100, image: product.image || "", tags: product.tags || [], delivery_type: product.delivery_type || "keys", delivery_content: product.delivery_content || "" } : blank);
  }, [open, product]);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    setBusy(true);
    try { const { data } = await api.post("/upload", fd); setF((x) => ({ ...x, image: data.url })); toast.success("Image uploaded"); }
    catch (e2) { toast.error(errMsg(e2)); } finally { setBusy(false); }
  };

  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    const body = { title: f.title, description: f.description, category: f.category, price: parseFloat(f.price), image: f.image || null,
      tags: f.tags, delivery_type: f.delivery_type, delivery_content: f.delivery_content };
    try {
      if (product) await api.put(`/vendor/products/${product.id}`, body); else await api.post("/vendor/products", body);
      toast.success("Submitted for admin review"); onOpenChange(false); onSaved();
    } catch (e2) { toast.error(errMsg(e2)); } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[92vh] overflow-y-auto border-[#272B29] bg-[#0E100F] sm:max-w-2xl" data-testid="product-form-dialog">
        <DialogHeader><DialogTitle className="font-display">{product ? "Edit product" : "New product"}</DialogTitle></DialogHeader>
        <form onSubmit={save} className="space-y-4">
          <Section icon={Eye} title="What buyers see" hint="Public on the marketplace" color="#22D3EE">
            <div><label className="nk-label">Title</label><input data-testid="pf-title-input" className="nk-input" required value={f.title} onChange={set("title")} /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="nk-label">Category</label>
                <select data-testid="pf-category-select" className="nk-input" value={f.category} onChange={set("category")}>{CATEGORIES.map((c) => <option key={c}>{c}</option>)}</select></div>
              <div><label className="nk-label">Price (USD)</label><input data-testid="pf-price-input" className="nk-input font-mono" type="number" min="0.01" step="0.01" required value={f.price} onChange={set("price")} /></div>
            </div>
            <div><label className="nk-label">Description shown to buyers</label><textarea data-testid="pf-description-input" className="nk-input min-h-[90px]" placeholder="What the product is, what's included, validity, region…" value={f.description} onChange={set("description")} /></div>
            <div><label className="nk-label">Tags (up to 8)</label><TagInput tags={f.tags} onChange={(tags) => setF({ ...f, tags })} /></div>
            <div>
              <label className="nk-label">Cover image</label>
              <div className="flex flex-wrap items-center gap-2">
                {DEFAULT_IMAGES.map((u, i) => (
                  <button type="button" key={u} data-testid={`pf-default-image-${i}`} onClick={() => setF({ ...f, image: u })}
                    className={`relative h-12 w-16 overflow-hidden rounded-md border-2 ${f.image === u ? "border-[#22C55E]" : "border-transparent opacity-70 hover:opacity-100"}`}>
                    <img src={u} alt="" className="h-full w-full object-cover" />
                    {f.image === u && <Check size={14} className="absolute right-0.5 top-0.5 rounded-full bg-[#22C55E] text-black" />}
                  </button>
                ))}
                <label className="nk-btn-ghost nk-btn-sm cursor-pointer"><Upload size={14} />Upload<input data-testid="pf-image-input" type="file" accept="image/*" className="hidden" onChange={upload} /></label>
              </div>
              <div className="mt-2 flex items-center gap-2 text-[11px] text-slate-500">
                {f.image && !DEFAULT_IMAGES.includes(f.image) && <img src={imgSrc(f.image)} alt="" className="h-8 w-12 rounded object-cover" />}
                {f.image ? <button type="button" data-testid="pf-image-clear" onClick={() => setF({ ...f, image: "" })} className="underline">Clear image</button> : "No image selected: a default image for the category will be used."}
              </div>
            </div>
          </Section>

          <Section icon={Lock} title="What buyers receive" hint="Private, revealed only after purchase" color="#A855F7">
            <div className="grid grid-cols-2 gap-2">
              {[["keys", "Unique key per buyer", KeyRound, "From your key stock"], ["content", "Same content for all", FileText, "Unlimited stock"]].map(([v, l, I, s]) => (
                <button type="button" key={v} data-testid={`pf-delivery-${v}`} onClick={() => setF({ ...f, delivery_type: v })}
                  className={`rounded-lg border p-3 text-left transition-colors ${f.delivery_type === v ? "border-[#22C55E]/60 bg-[#22C55E]/10" : "border-[#272B29]"}`}>
                  <div className="flex items-center gap-2 text-sm font-semibold"><I size={15} />{l}</div><div className="text-[11px] text-slate-500">{s}</div>
                </button>
              ))}
            </div>
            <div>
              <label className="nk-label">{f.delivery_type === "keys" ? "Delivery box: instructions sent with each key (optional)" : "Delivery box: the digital goods the buyer receives (required)"}</label>
              <textarea data-testid="pf-delivery-content-input" className="nk-input min-h-[120px] font-mono text-xs" required={f.delivery_type === "content"}
                placeholder={f.delivery_type === "keys" ? "e.g. Redeem at the official portal → Account → Activate key" : "e.g. Download link, access code, account invite, file password, setup steps…"}
                value={f.delivery_content} onChange={set("delivery_content")} />
            </div>
            {f.delivery_type === "keys" && <p className="text-[11px] text-slate-500">After saving, add license keys from the <b>Keys</b> button. Each buyer gets one unique key.</p>}
          </Section>

          <p className="text-xs text-slate-500">Saving sends the listing to admin review. Admin may adjust the final price.</p>
          <button data-testid="pf-submit-btn" disabled={busy} className="nk-btn-primary w-full">{product ? "Save & resubmit" : "Submit for review"}</button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
