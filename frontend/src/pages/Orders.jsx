import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, money, fmtDate } from "@/lib/api";
import { PageHeader, Empty, StatusBadge } from "@/components/Shared";

export default function Orders() {
  const [orders, setOrders] = useState(null);
  useEffect(() => { api.get("/orders").then((r) => setOrders(r.data)); }, []);
  return (
    <div>
      <PageHeader eyebrow="Purchases" title="Order history" />
      {orders === null ? <div className="nk-card h-40 animate-pulse" /> : !orders.length ? <Empty testId="orders-empty" text="No orders yet." /> : (
        <div className="nk-card overflow-x-auto">
          <table className="nk-table" data-testid="orders-table">
            <thead><tr><th>Date</th><th>Product</th><th>Vendor</th><th>Status</th><th className="text-right">Price</th></tr></thead>
            <tbody>{orders.map((o) => (
              <tr key={o.id} data-testid={`order-row-${o.id}`}>
                <td className="font-mono text-xs">{fmtDate(o.created_at)}</td>
                <td><Link to={`/product/${o.product_id}`} className="hover:text-brand">{o.product_title}</Link></td>
                <td className="text-xs">{o.vendor_name}</td>
                <td><StatusBadge status={o.status} /></td>
                <td className="text-right font-mono text-brand">{money(o.price_cents)}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}
