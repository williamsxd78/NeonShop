import { useState } from "react";
import { toast } from "sonner";
import { api, errMsg, money, fmtDate, imgSrc } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { StatusBadge, Empty, FilterTabs, PromptDialog } from "@/components/Shared";

export function AdminListings({ onChange }) {
  const [status, setStatus] = useState("pending");
  const [list, reload] = useFetch("/admin/products", { status });
  const [approve, setApprove] = useState(null);
  const [reject, setReject] = useState(null);
  const [price, setPrice] = useState(null);
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
                  <div><div className="font-medium text-slate-100">{p.title}</div><div className="text-xs text-slate-500">{p.category} · {fmtDate(p.created_at)}</div></div></div></td>
                <td className="text-xs">{p.vendor_name}</td>
                <td className="font-mono">{money(p.vendor_price_cents ?? p.price_cents)}</td>
                <td className="font-mono text-[#22C55E]">{money(p.price_cents)}</td>
                <td className="font-mono">{p.stock_count}</td>
                <td><StatusBadge status={p.status} /></td>
                <td className="whitespace-nowrap text-right">
                  {p.status !== "approved" && <button data-testid={`listing-approve-${p.id}`} onClick={() => setApprove(p)} className="nk-btn-primary nk-btn-sm mr-2">Approve</button>}
                  {p.status !== "rejected" && <button data-testid={`listing-reject-${p.id}`} onClick={() => setReject(p)} className="nk-btn-danger nk-btn-sm mr-2">Reject</button>}
                  <button data-testid={`listing-price-${p.id}`} onClick={() => setPrice(p)} className="nk-btn-ghost nk-btn-sm">Price</button>
                </td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
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
