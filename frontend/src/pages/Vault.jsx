import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHeader, Empty } from "@/components/Shared";
import { KeyCard } from "@/components/DeliveryView";

export default function Vault() {
  const [orders, setOrders] = useState(null);
  useEffect(() => { api.get("/orders").then((r) => setOrders(r.data)); }, []);
  return (
    <div>
      <PageHeader eyebrow="Secure storage" title="Key vault" />
      {orders === null ? <div className="nk-card h-40 animate-pulse" /> : !orders.length ? <Empty testId="vault-empty" text="Your vault is empty. Purchased goods appear here instantly." /> : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="vault-grid">{orders.map((o) => <KeyCard key={o.id} o={o} />)}</div>
      )}
    </div>
  );
}
