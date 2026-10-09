import { useState } from "react";
import { toast } from "sonner";
import { api, errMsg, money, fmtDate, imgSrc } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { StatusBadge, Empty, FilterTabs, PromptDialog, ConfirmDialog } from "@/components/Shared";
import { Trash2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

const Preview = ({ p, onClose }) => (
  <Dialog open={!!p} onOpenChange={(o) => !o && onClose()}>
    <DialogContent className="max-h-[90vh] overflow-y-auto border-[#272B29] bg-[#0E100F] sm:max-w-lg" data-testid="listing-preview-dialog">
      <DialogHeader><DialogTitle className="font-display">{p?.title}</DialogTitle></DialogHeader>
      {p && <div className="space-y-4 text-sm">
        {p.image && <img src={imgSrc(p.image)} alt="" className="h-40 w-full rounded-lg object-cover" />}
        <div><div className="nk-label">Shown to buyers</div><p className="whitespace-pre-line text-slate-300">{p.description || "-"}</p></div>
        <div className="flex flex-wrap gap-1.5">{(p.tags || []).map((t) => <span key={t} className="rounded-md border border-[#272B29] px-2 py-0.5 font-mono text-[11px] uppercase text-slate-400">#{t}</span>)}</div>
        <div><div className="nk-label">Buyer receives · {p.delivery_type === "content" ? "same content for all (unlimited)" : `unique key (${p.stock_count} in stock)`}</div>
          <pre data-testid="listing-preview-content" className="max-h-48 overflow-auto whitespace-pre-wrap rounded-lg border border-[#A855F7]/25 bg-[#A855F7]/[0.06] p-3 font-mono text-xs">{p.delivery_content || "(no extra content)"}</pre></div>
      </div>}
    </DialogContent>
  </Dialog>
);

export function AdminListings({ onChange }) {
  const [status, setStatus] = useState("pending");
  const [list, reload] = useFetch("/admin/products", { status });
  const [approve, setApprove] = useState(null);
  const [reject, setReject] = useState(null);
  const [price, setPrice] = useState(null);
  const [preview, setPreview] = useState(null);
  const [batch, setBatch] = useState(null);
  const [del, setDel] = useState(null);
  const batchCount = (b) => list.filter((x) => x.batch_id === b && x.status !== "approved").length;
  const done = () => { reload(); onChange(); };
  const call = async (fn, msg) => { try { await fn(); toast.success(msg); done(); } catch (e) { toast.error(errMsg(e)); throw e; } };

  return (
    <div>
      <FilterTabs value={status} onChange={setStatus} options={["pending", "approved", "rejected", "all"]} testPrefix="listing-filter" />
      {!list?.length ? <Empty testId="admin-listings-empty" text="No listings here." /> : (
        <div className="nk-card overflow-x-auto">
          <table className="nk-table" data-testid="admin-listings-table">
            <thead><tr><th>Product</th><th>Vendor</th><th>Vendor price</th><th>Live price</th><th>Stock</th><th>Status</th><th /></tr></thead>
            <tbody>{list.map((p) => (
              <tr key={p.id} data-testid={`admin-listing-row-${p.id}`}>
                <td><div className="flex items-center gap-3">{p.image && <img src={imgSrc(p.image)} alt="" className="h-9 w-12 rounded object-cover" />}
                  <div><div className="font-medium text-slate-100">{p.title}</div><div className="text-xs text-slate-500">{p.category} · {fmtDate(p.created_at)}{p.batch_id && <span className="font-mono"> · batch {p.batch_id.slice(0, 6)}</span>}</div></div></div></td>
                <td className="text-xs">{p.vendor_name}</td>
                <td className="font-mono">{money(p.vendor_price_cents ?? p.price_cents)}</td>
                <td className="font-mono text-[#22C55E]">{money(p.price_cents)}</td>
                <td className="font-mono">{p.delivery_type === "content" ? "∞" : p.stock_count}</td>
                <td><StatusBadge status={p.status} /></td>
                <td className="whitespace-nowrap text-right">
                  <button data-testid={`listing-preview-${p.id}`} onClick={() => setPreview(p)} className="nk-btn-ghost nk-btn-sm mr-2">Preview</button>
                  {p.batch_id && p.status !== "approved" && <button data-testid={`listing-approve-batch-${p.id}`} onClick={() => setBatch(p)} className="nk-btn-primary nk-btn-sm mr-2">Approve batch ({batchCount(p.batch_id)})</button>}
                  {p.status !== "approved" && <button data-testid={`listing-approve-${p.id}`} onClick={() => setApprove(p)} className="nk-btn-primary nk-btn-sm mr-2">Approve</button>}
                  {p.status !== "rejected" && <button data-testid={`listing-reject-${p.id}`} onClick={() => setReject(p)} className="nk-btn-danger nk-btn-sm mr-2">Reject</button>}
                  <button data-testid={`listing-price-${p.id}`} onClick={() => setPrice(p)} className="nk-btn-ghost nk-btn-sm mr-2">Price</button>
                  <button data-testid={`listing-delete-${p.id}`} onClick={() => setDel(p)} className="nk-btn-danger nk-btn-sm"><Trash2 size={14} /></button>
                </td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
      <Preview p={preview} onClose={() => setPreview(null)} />
      <PromptDialog testId="batch-approve" open={!!batch} onOpenChange={(o) => !o && setBatch(null)} title="Approve whole batch"
        description="Publishes every pending item from this bulk import. Optionally set one live price for all." label="Live price for all (USD)" type="number"
        defaultValue={batch ? (batch.price_cents / 100).toFixed(2) : ""} confirmText="Approve batch"
        onSubmit={(v) => call(() => api.post(`/admin/batches/${batch.batch_id}/approve`, { price: parseFloat(v) }), "Batch is live")} />
      <ConfirmDialog testId="listing-delete" open={!!del} onOpenChange={(o) => !o && setDel(null)} title={`Delete "${del?.title}"?`}
        description="Permanently deletes this listing and its unsold stock. Past orders stay intact."
        onConfirm={() => call(() => api.delete(`/admin/products/${del.id}`), "Listing deleted").catch(() => {})} />
      <PromptDialog testId="listing-approve" open={!!approve} onOpenChange={(o) => !o && setApprove(null)} title="Approve listing"
        description="Optionally override the vendor's price before going live." label="Live price (USD)" type="number"
        defaultValue={approve ? (approve.price_cents / 100).toFixed(2) : ""} confirmText="Approve & publish"
        onSubmit={(v) => call(() => api.post(`/admin/products/${approve.id}/approve`, { price: parseFloat(v) }), "Listing is live")} />
      <PromptDialog testId="listing-reject" open={!!reject} onOpenChange={(o) => !o && setReject(null)} title="Reject listing" label="Reason" danger confirmText="Reject"
        onSubmit={(v) => call(() => api.post(`/admin/products/${reject.id}/reject`, { reason: v }), "Listing rejected")} />
      <PromptDialog testId="listing-price" open={!!price} onOpenChange={(o) => !o && setPrice(null)} title="Price override" label="New price (USD)" type="number"
        defaultValue={price ? (price.price_cents / 100).toFixed(2) : ""} confirmText="Override price"
        onSubmit={(v) => call(() => api.put(`/admin/products/${price.id}/price`, { price: parseFloat(v) }), "Price updated")} />
    </div>
  );
}
