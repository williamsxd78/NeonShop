import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, ShieldCheck, Zap, Package } from "lucide-react";
import { api, errMsg, money, imgSrc } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { DeliveryView } from "@/components/DeliveryView";

export default function ProductDetail() {
  const { id } = useParams();
  const { user, refresh } = useAuth();
  const nav = useNavigate();
  const [p, setP] = useState(null);
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [order, setOrder] = useState(null);

  const load = () => api.get(`/products/${id}`).then((r) => setP(r.data)).catch(() => setP(false));
  useEffect(() => { load(); }, [id]); // eslint-disable-line

  const buy = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/orders", { product_id: id });
      setConfirm(false); setOrder(data.order);
      toast.success("Delivered to your vault");
      refresh(); load();
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };

  if (p === null) return <div className="nk-card h-96 animate-pulse" />;
  if (p === false) return <div className="text-slate-400">Product not found. <Link to="/" className="text-[#22C55E]">Back to market</Link></div>;
  const short = user && user.balance_cents < p.price_cents;
  const unlimited = p.delivery_type === "content";
  const soldOut = !unlimited && p.stock_count < 1;

  return (
    <div className="nk-rise">
      <Link to="/" data-testid="back-to-market" className="mb-6 inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"><ArrowLeft size={16} />Marketplace</Link>
      <div className="grid gap-8 lg:grid-cols-[1.3fr_1fr]">
        <div className="nk-card overflow-hidden">
          <div className="aspect-[16/10] bg-[#0E100F]">
            {p.image ? <img src={imgSrc(p.image)} alt={p.title} className="h-full w-full object-cover" /> : <div className="grid h-full place-items-center text-slate-600"><Package size={48} /></div>}
          </div>
          <div className="p-6">
            <h3 className="mb-2 text-lg font-semibold">About this product</h3>
            <p className="whitespace-pre-line text-sm leading-relaxed text-slate-400" data-testid="product-description">{p.description || "No description provided."}</p>
          </div>
        </div>
        <div className="space-y-5">
          <div className="nk-card p-6">
            <div className="nk-eyebrow mb-3">{p.category}</div>
            <h1 data-testid="product-title" className="text-2xl font-semibold tracking-tight">{p.title}</h1>
            <p className="mt-2 text-sm text-slate-500">Sold by <span className="text-slate-300">{p.vendor_name}</span> · {p.sales_count} sold</p>
            <div className="mt-6 flex items-end justify-between">
              <span data-testid="product-price" className="font-mono text-3xl text-[#22C55E]">{money(p.price_cents)}</span>
              <span data-testid="product-stock" className={`font-mono text-sm ${!soldOut ? "text-[#4ADE80]" : "text-[#FF2A5F]"}`}>{unlimited ? "Instant · unlimited" : p.stock_count > 0 ? `${p.stock_count} in stock` : "Out of stock"}</span>
            </div>
            {p.tags?.length > 0 && <div className="mt-4 flex flex-wrap gap-1.5" data-testid="product-tags">{p.tags.map((t) => <span key={t} className="rounded-md border border-[#272B29] px-2 py-0.5 font-mono text-[11px] uppercase text-slate-400">#{t}</span>)}</div>}
            {user ? (
              <>
                <button data-testid="buy-now-btn" disabled={soldOut} onClick={() => (short ? nav("/wallet") : setConfirm(true))} className="nk-btn-primary mt-6 w-full py-3">
                  <Zap size={16} />{short ? "Add funds to buy" : "Buy instantly"}
                </button>
                <p className="mt-3 text-center font-mono text-xs text-slate-500">Wallet balance: <span data-testid="detail-balance" className="text-slate-300">{money(user.balance_cents)}</span></p>
              </>
            ) : (
              <Link to="/login" data-testid="login-to-buy" className="nk-btn-primary mt-6 w-full py-3">Log in to buy</Link>
            )}
          </div>
          <div className="nk-card flex gap-3 p-5 text-sm text-slate-400">
            <ShieldCheck className="shrink-0 text-[#4ADE80]" size={20} />
            <p>Keys are reserved atomically and delivered instantly. <span className="text-slate-300">Delivered keys are non-refundable</span>; disputes are resolved by admin via wallet credit.</p>
          </div>
        </div>
      </div>

      <Dialog open={confirm} onOpenChange={setConfirm}>
        <DialogContent className="border-[#272B29] bg-[#121413]" data-testid="buy-confirm-dialog">
          <DialogHeader><DialogTitle className="font-display">Confirm purchase</DialogTitle></DialogHeader>
          <div className="space-y-2 font-mono text-sm">
            <div className="flex justify-between"><span className="text-slate-500">Item</span><span className="text-right">{p.title}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Price</span><span className="text-[#22C55E]">{money(p.price_cents)}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Balance after</span><span>{money((user?.balance_cents || 0) - p.price_cents)}</span></div>
          </div>
          <p className="text-xs text-slate-500">No refunds on delivered keys.</p>
          <button data-testid="confirm-buy-btn" disabled={busy} onClick={buy} className="nk-btn-primary w-full">{busy ? "Processing…" : "Pay from wallet"}</button>
        </DialogContent>
      </Dialog>

      <Dialog open={!!order} onOpenChange={(o) => !o && setOrder(null)}>
        <DialogContent className="border-[#4ADE80]/30 bg-[#121413]" data-testid="order-success-dialog">
          <DialogHeader><DialogTitle className="font-display text-[#4ADE80]">Purchase delivered</DialogTitle></DialogHeader>
          <div data-testid="delivered-goods">{order && <DeliveryView o={order} />}</div>
          <Link to="/vault" data-testid="go-to-vault" className="nk-btn-ghost w-full">Open vault</Link>
        </DialogContent>
      </Dialog>
    </div>
  );
}
