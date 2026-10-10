import { useEffect, useState } from "react";
import { api, money, fmtDate, COIN_LABEL } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { AddFunds } from "@/components/AddFunds";
import { PageHeader, StatusBadge, Empty } from "@/components/Shared";
import { ChainStatus } from "@/components/ChainStatus";

export default function Wallet() {
  const { user, refresh } = useAuth();
  const [w, setW] = useState(null);
  const load = () => { api.get("/wallet").then((r) => setW(r.data)); refresh(); };
  useEffect(() => { load(); }, []); // eslint-disable-line
  const watching = w?.deposits?.some((d) => d.status === "pending" && d.chain && !d.chain.final);
  useEffect(() => {
    if (!watching) return undefined;
    const t = setInterval(load, 20000);
    return () => clearInterval(t);
  }, [watching]); // eslint-disable-line

  return (
    <div>
      <PageHeader eyebrow="Wallet · USD equivalent" title="Wallet">
        <div className="nk-card px-6 py-4 text-right">
          <div className="nk-label">Available balance</div>
          <div data-testid="wallet-balance" className="font-mono text-2xl text-brandlt">{money(w?.balance_cents ?? user?.balance_cents)}</div>
        </div>
      </PageHeader>
      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <AddFunds onDone={load} />
        <div className="nk-card p-6">
          <h2 className="mb-4 text-lg font-bold">Deposit requests</h2>
          {!w?.deposits?.length ? <Empty testId="deposits-empty" text="No deposits yet." /> : (
            <div className="space-y-2" data-testid="deposit-history">
              {w.deposits.map((d) => (
                <div key={d.id} data-testid={`deposit-row-${d.id}`} className="rounded-lg border border-line bg-deep p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-sm">{d.reference} · {COIN_LABEL[d.coin]}</span>
                    <StatusBadge status={d.status} />
                  </div>
                  <div className="mt-1 flex justify-between font-mono text-xs text-slate-500">
                    <span>{money(d.credited_cents ?? d.amount_cents)}</span><span>{fmtDate(d.created_at)}</span>
                  </div>
                  <ChainStatus d={d} testId={`deposit-chain-${d.id}`} />
                  {d.reason && <p className="mt-1 text-xs text-[#FF2A5F]">Reason: {d.reason}</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="nk-card mt-6 overflow-x-auto p-6">
        <h2 className="mb-4 text-lg font-bold">Balance history</h2>
        {!w?.transactions?.length ? <Empty text="No balance changes yet." /> : (
          <table className="nk-table" data-testid="wallet-transactions">
            <thead><tr><th>Date</th><th>Type</th><th>Details</th><th className="text-right">Amount</th></tr></thead>
            <tbody>{w.transactions.map((t) => (
              <tr key={t.id}><td className="font-mono text-xs">{fmtDate(t.created_at)}</td><td className="font-mono text-xs">{t.action}</td><td className="text-xs">{t.details}</td>
                <td className={`text-right font-mono ${t.amount_cents >= 0 ? "text-brandlt" : "text-[#FF2A5F]"}`}>{t.amount_cents >= 0 ? "+" : "-"}{money(Math.abs(t.amount_cents))}</td></tr>
            ))}</tbody>
          </table>
        )}
      </div>
    </div>
  );
}
