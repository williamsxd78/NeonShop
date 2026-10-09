import { useState } from "react";
import { Plus, Clock, XCircle, Layers, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg, money, fmtDate } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { useAuth } from "@/context/AuthContext";
import { PageHeader, Stat, StatusBadge, Empty, FilterTabs, ConfirmDialog, PromptDialog } from "@/components/Shared";
import { BulkImport } from "@/components/vendor/BulkImport";
import { ProductForm } from "@/components/vendor/ProductForm";
import { KeysDialog } from "@/components/vendor/KeysDialog";
import { VendorWithdrawals } from "@/components/vendor/VendorWithdrawals";

function ProductsTab({ products, reload }) {
  const [edit, setEdit] = useState(undefined);
  const [keysFor, setKeysFor] = useState(null);
  const [bulk, setBulk] = useState(false);
  const [del, setDel] = useState(null);
  const [sel, setSel] = useState([]);
  const [bulkPrice, setBulkPrice] = useState(false);
  const allOn = products?.length > 0 && sel.length === products.length;
  const toggle = (id) => setSel(sel.includes(id) ? sel.filter((x) => x !== id) : [...sel, id]);
  const selectBatch = (b) => setSel([...new Set([...sel, ...products.filter((p) => p.batch_id === b).map((p) => p.id)])]);
  const batches = Object.entries((products || []).reduce((a, p) => (p.batch_id ? { ...a, [p.batch_id]: (a[p.batch_id] || 0) + 1 } : a), {}));
  const doDelete = async () => {
    try {
      const { data } = del.ids ? await api.post("/vendor/products/bulk-delete", { ids: del.ids })
        : await api.delete(del.batch ? `/vendor/batches/${del.batch}` : `/vendor/products/${del.p.id}`);
      toast.success(`Deleted ${data.deleted} product(s)`); setSel([]); reload();
    } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <>
      <div className="mb-4 flex flex-wrap justify-end gap-2">
        <button data-testid="vendor-bulk-import-btn" onClick={() => setBulk(true)} className="nk-btn-ghost"><Layers size={16} />Bulk import</button>
        <button data-testid="vendor-new-product-btn" onClick={() => setEdit(null)} className="nk-btn-primary"><Plus size={16} />New product</button>
      </div>
      {batches.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-2" data-testid="vendor-batches">{batches.map(([b, n]) => (
          <span key={b} className="flex items-center gap-2 rounded-lg border border-[#272B29] bg-[#121413] px-3 py-1.5 font-mono text-[11px] text-slate-400">
            <button data-testid={`vendor-select-batch-${b}`} onClick={() => selectBatch(b)} className="hover:text-white" title="Select all items in batch">Batch {b.slice(0, 6)} · {n} items</button>
            <button data-testid={`vendor-delete-batch-${b}`} onClick={() => setDel({ batch: b, n })} className="text-[#FF2A5F] hover:text-[#FF6B8B]"><Trash2 size={13} /></button>
          </span>
        ))}</div>
      )}
      {sel.length > 0 && (
        <div data-testid="vendor-selection-bar" className="sticky top-16 z-20 mb-3 flex flex-wrap items-center gap-2 rounded-xl border border-[#22C55E]/40 bg-[#0E100F]/95 p-3 backdrop-blur">
          <span data-testid="vendor-selected-count" className="font-mono text-sm text-[#4ADE80]">{sel.length} selected</span>
          <button data-testid="vendor-bulk-price-btn" onClick={() => setBulkPrice(true)} className="nk-btn-primary nk-btn-sm ml-auto">Set price</button>
          <button data-testid="vendor-bulk-delete-btn" onClick={() => setDel({ ids: sel })} className="nk-btn-danger nk-btn-sm"><Trash2 size={14} />Delete</button>
          <button data-testid="vendor-clear-selection" onClick={() => setSel([])} className="nk-btn-ghost nk-btn-sm">Clear</button>
        </div>
      )}
      {!products?.length ? <Empty testId="vendor-products-empty" text="No products yet. Create your first listing." /> : (
        <div className="nk-card overflow-x-auto">
          <table className="nk-table" data-testid="vendor-products-table">
            <thead><tr><th className="w-8"><input type="checkbox" data-testid="vendor-select-all" className="accent-[#22C55E]" checked={allOn} onChange={() => setSel(allOn ? [] : products.map((p) => p.id))} /></th><th>Product</th><th>Category</th><th>Your price</th><th>Live price</th><th>Stock</th><th>Status</th><th /></tr></thead>
            <tbody>{products.map((p) => (
              <tr key={p.id} data-testid={`vendor-product-row-${p.id}`} className={sel.includes(p.id) ? "bg-[#22C55E]/[0.05]" : ""}>
                <td><input type="checkbox" data-testid={`vendor-select-${p.id}`} className="accent-[#22C55E]" checked={sel.includes(p.id)} onChange={() => toggle(p.id)} /></td>
                <td className="font-medium text-slate-100">{p.title}<div className="font-mono text-[10px] uppercase text-slate-500">{p.delivery_type === "content" ? "content delivery" : "key delivery"}{p.tags?.length ? ` · #${p.tags.join(" #")}` : ""}</div>{p.reason && <div className="text-xs text-[#FF2A5F]">{p.reason}</div>}</td>
                <td className="text-xs">{p.category}</td>
                <td className="font-mono">{money(p.vendor_price_cents ?? p.price_cents)}</td>
                <td className="font-mono text-[#22C55E]">{money(p.price_cents)}</td>
                <td className="font-mono">{p.delivery_type === "content" ? "∞" : p.stock_count}</td>
                <td><StatusBadge status={p.status} /></td>
                <td className="whitespace-nowrap text-right">
                  {p.delivery_type !== "content" && <button data-testid={`vendor-keys-btn-${p.id}`} onClick={() => setKeysFor(p)} className="nk-btn-ghost nk-btn-sm mr-2">Keys</button>}
                  <button data-testid={`vendor-edit-btn-${p.id}`} onClick={() => setEdit(p)} className="nk-btn-ghost nk-btn-sm mr-2">Edit</button>
                  <button data-testid={`vendor-delete-btn-${p.id}`} onClick={() => setDel({ p })} className="nk-btn-danger nk-btn-sm" title="Delete"><Trash2 size={14} /></button>
                </td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
      <ProductForm open={edit !== undefined} onOpenChange={(o) => !o && setEdit(undefined)} product={edit} onSaved={reload} />
      <BulkImport open={bulk} onOpenChange={setBulk} onDone={reload} />
      <ConfirmDialog testId="vendor-delete" open={!!del} onOpenChange={(o) => !o && setDel(null)} onConfirm={doDelete}
        title={del?.ids ? `Delete ${del.ids.length} selected product(s)?` : del?.batch ? `Delete batch (${del.n} items)?` : `Delete "${del?.p?.title}"?`}
        description="This permanently deletes the listing(s) and all unsold stock. Past orders and buyers' vaults are not affected." />
      <PromptDialog testId="vendor-bulk-price" open={bulkPrice} onOpenChange={setBulkPrice} title={`Set price for ${sel.length} listing(s)`}
        description="Changed listings go back to admin review before going live again." label="New price (USD)" type="number" confirmText="Update prices"
        onSubmit={async (v) => { try { const { data } = await api.post("/vendor/products/bulk-price", { ids: sel, price: parseFloat(v) }); toast.success(`${data.updated} listing(s) updated, pending review`); setSel([]); reload(); } catch (e) { toast.error(errMsg(e)); throw e; } }} />
      <KeysDialog product={keysFor} onOpenChange={(o) => !o && setKeysFor(null)} onChanged={reload} />
    </>
  );
}

function SalesTab() {
  const [sales] = useFetch("/vendor/sales");
  if (!sales?.length) return <Empty testId="vendor-sales-empty" text="No sales yet." />;
  return (
    <div className="nk-card overflow-x-auto">
      <table className="nk-table" data-testid="vendor-sales-table">
        <thead><tr><th>Date</th><th>Product</th><th>Buyer</th><th>Price</th><th>Commission</th><th className="text-right">You earned</th></tr></thead>
        <tbody>{sales.map((s) => (
          <tr key={s.id}><td className="font-mono text-xs">{fmtDate(s.created_at)}</td><td>{s.product_title}</td><td className="text-xs">{s.buyer_email}</td>
            <td className="font-mono">{money(s.price_cents)}</td><td className="font-mono text-xs text-slate-500">{s.commission_pct}% · {money(s.commission_cents)}</td>
            <td className="text-right font-mono text-[#4ADE80]">{money(s.vendor_earning_cents)}</td></tr>
        ))}</tbody>
      </table>
    </div>
  );
}

export default function VendorDashboard({ embedded }) {
  const { user, refresh } = useAuth();
  const [tab, setTab] = useState("overview");
  const [stats, reloadStats] = useFetch("/vendor/stats");
  const [products, reloadProducts] = useFetch("/vendor/products");
  const reload = () => { reloadStats(); reloadProducts(); refresh(); };

  const isAdmin = user.role === "admin";
  if (!isAdmin && user.vendor_status !== "approved") {
    const rejected = user.vendor_status === "rejected";
    return (
      <div className="nk-card mx-auto mt-10 max-w-lg p-10 text-center" data-testid="vendor-not-approved">
        {rejected ? <XCircle className="mx-auto mb-4 text-[#FF2A5F]" size={40} /> : <Clock className="mx-auto mb-4 text-[#FFB800]" size={40} />}
        <h2 className="text-2xl font-bold">{rejected ? "Application rejected" : "Awaiting approval"}</h2>
        <p className="mt-2 text-sm text-slate-400">{rejected ? "Your vendor application was not approved. Check notifications for details." : "An admin is reviewing your vendor application. You'll be notified once approved."}</p>
      </div>
    );
  }

  return (
    <div>
      {!embedded && <PageHeader eyebrow={user.store_name} title="Vendor dashboard" />}
      {isAdmin && <p className="mb-4 text-xs text-slate-500" data-testid="admin-store-note">Sold as <b className="text-slate-300">NeonKeys Official</b>. Your listings go live instantly and 100% of each sale is platform revenue.</p>}
      <FilterTabs value={tab} onChange={setTab} options={isAdmin ? ["overview", "products", "sales"] : ["overview", "products", "sales", "withdrawals"]} testPrefix="vendor-tab" />
      {tab === "overview" && stats && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4" data-testid="vendor-overview">
          <Stat testId="vstat-earnings" label="Earnings balance" value={money(stats.earnings_cents)} accent="#4ADE80" />
          <Stat testId="vstat-sales" label="Total sales" value={stats.total_sales} />
          <Stat testId="vstat-gross" label="Gross volume" value={money(stats.gross_cents)} accent="#A855F7" />
          <Stat testId="vstat-commission" label="Your commission rate" value={`${stats.commission_pct}%`} accent="#FFB800" />
          <Stat label="Products" value={stats.products} />
          <Stat label="Live listings" value={stats.live_products} accent="#4ADE80" />
          <Stat label="Net earned (all time)" value={money(stats.net_cents)} accent="#4ADE80" />
        </div>
      )}
      {tab === "products" && <ProductsTab products={products} reload={reload} />}
      {tab === "sales" && <SalesTab />}
      {tab === "withdrawals" && <VendorWithdrawals earnings={stats?.earnings_cents} onChanged={reload} />}
    </div>
  );
}
