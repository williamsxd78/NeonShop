import { useState } from "react";
import { toast } from "sonner";
import { Copy } from "lucide-react";
import { api, errMsg, money, fmtDate, COIN_LABEL } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { StatusBadge, Empty, FilterTabs, PromptDialog } from "@/components/Shared";

export function AdminWithdrawals({ onChange }) {
  const [status, setStatus] = useState("pending");
  const [list, reload] = useFetch("/admin/withdrawals", { status });
  const [pay, setPay] = useState(null);
  const [reject, setReject] = useState(null);
  const done = () => { reload(); onChange(); };

  return (
    <div>
      <FilterTabs value={status} onChange={setStatus} options={["pending", "paid", "rejected", "all"]} testPrefix="wd-filter" />
      {!list?.length ? <Empty testId="admin-withdrawals-empty" text="No withdrawal requests here." /> : (
        <div className="nk-card overflow-x-auto">
          <table className="nk-table" data-testid="admin-withdrawals-table">
            <thead><tr><th>Date</th><th>Vendor</th><th>Amount</th><th>Coin</th><th>Address</th><th>Status</th><th /></tr></thead>
            <tbody>{list.map((w) => (
              <tr key={w.id} data-testid={`admin-wd-row-${w.id}`}>
                <td className="font-mono text-xs">{fmtDate(w.created_at)}</td>
                <td className="text-xs">{w.vendor_name}<div className="text-slate-500">{w.vendor_email}</div></td>
                <td className="font-mono text-brand">{money(w.amount_cents)}</td>
                <td className="text-xs">{COIN_LABEL[w.coin]}</td>
                <td className="max-w-[200px]"><div className="flex items-center gap-1"><span className="truncate font-mono text-xs">{w.address}</span>
                  <button onClick={() => { navigator.clipboard.writeText(w.address); toast.success("Copied"); }} className="text-slate-500 hover:text-white"><Copy size={12} /></button></div></td>
                <td><StatusBadge status={w.status} />{w.payout_txid && <div className="mt-1 max-w-[140px] truncate font-mono text-[10px] text-slate-500">{w.payout_txid}</div>}</td>
                <td className="whitespace-nowrap text-right">{w.status === "pending" && <>
                  <button data-testid={`wd-pay-${w.id}`} onClick={() => setPay(w)} className="nk-btn-primary nk-btn-sm mr-2">Mark paid</button>
                  <button data-testid={`wd-reject-${w.id}`} onClick={() => setReject(w)} className="nk-btn-danger nk-btn-sm">Reject</button></>}
                </td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
      <PromptDialog testId="wd-pay" open={!!pay} onOpenChange={(o) => !o && setPay(null)} title="Mark payout as paid" required={false}
        description={pay && `Send ${money(pay.amount_cents)} in ${COIN_LABEL[pay.coin]} to ${pay.address}, then record the payout TXID.`}
        label="Payout TXID (optional)" confirmText="Mark paid"
        onSubmit={async (v) => { try { await api.post(`/admin/withdrawals/${pay.id}/pay`, { payout_txid: v || null }); toast.success("Marked as paid"); done(); } catch (e) { toast.error(errMsg(e)); throw e; } }} />
      <PromptDialog testId="wd-reject" open={!!reject} onOpenChange={(o) => !o && setReject(null)} title="Reject withdrawal" description="Funds return to the vendor's earnings." label="Reason" danger confirmText="Reject"
        onSubmit={async (v) => { try { await api.post(`/admin/withdrawals/${reject.id}/reject`, { reason: v }); toast.success("Rejected & refunded"); done(); } catch (e) { toast.error(errMsg(e)); throw e; } }} />
    </div>
  );
}
