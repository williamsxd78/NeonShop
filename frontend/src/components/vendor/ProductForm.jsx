import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Upload } from "lucide-react";
import { api, errMsg, CATEGORIES, imgSrc } from "@/lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

const blank = { title: "", description: "", category: CATEGORIES[0], price: "", image: "" };

export function ProductForm({ open, onOpenChange, product, onSaved }) {
  const [f, setF] = useState(blank);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (open) setF(product ? { ...product, price: (product.vendor_price_cents ?? product.price_cents) / 100, image: product.image || "" } : blank);
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
    const body = { title: f.title, description: f.description, category: f.category, price: parseFloat(f.price), image: f.image || null };
    try {
      if (product) await api.put(`/vendor/products/${product.id}`, body); else await api.post("/vendor/products", body);
      toast.success("Submitted for admin review"); onOpenChange(false); onSaved();
    } catch (e2) { toast.error(errMsg(e2)); } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto border-[#272B29] bg-[#121413] sm:max-w-lg" data-testid="product-form-dialog">
        <DialogHeader><DialogTitle className="font-display">{product ? "Edit product" : "New product"}</DialogTitle></DialogHeader>
        <form onSubmit={save} className="space-y-4">
          <div><label className="nk-label">Title</label><input data-testid="pf-title-input" className="nk-input" required value={f.title} onChange={set("title")} /></div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="nk-label">Category</label>
              <select data-testid="pf-category-select" className="nk-input" value={f.category} onChange={set("category")}>{CATEGORIES.map((c) => <option key={c}>{c}</option>)}</select></div>
            <div><label className="nk-label">Price (USD)</label><input data-testid="pf-price-input" className="nk-input font-mono" type="number" min="0.01" step="0.01" required value={f.price} onChange={set("price")} /></div>
          </div>
          <div><label className="nk-label">Description</label><textarea data-testid="pf-description-input" className="nk-input min-h-[100px]" value={f.description} onChange={set("description")} /></div>
          <div>
            <label className="nk-label">Cover image</label>
            <div className="flex items-center gap-3">
              {f.image && <img src={imgSrc(f.image)} alt="" className="h-14 w-20 rounded-md object-cover" />}
              <label className="nk-btn-ghost nk-btn-sm cursor-pointer"><Upload size={14} />Upload<input data-testid="pf-image-input" type="file" accept="image/*" className="hidden" onChange={upload} /></label>
            </div>
          </div>
          <p className="text-xs text-slate-500">Saving sends the listing to admin review. Admin may adjust the final price.</p>
          <button data-testid="pf-submit-btn" disabled={busy} className="nk-btn-primary w-full">{product ? "Save & resubmit" : "Submit for review"}</button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
