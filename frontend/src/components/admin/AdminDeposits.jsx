import { useState } from "react";
import { toast } from "sonner";
import { api, errMsg, money, fmtDate, COIN_LABEL } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { StatusBadge, Empty, FilterTabs, PromptDialog } from "@/components/Shared";
import { ManualDeposit } from "@/components/admin/ManualDeposit";
import { Plus } from "lucide-react";

export function AdminDeposits({ onChange }) {
  const [status, setStatus] = useState("pending");
  const [list, reload] = useFetch("/admin/deposits", { status });
  const [approve, setApprove] = useState(null);
  const [reject, setReject] = useState(null);
  const [manual, setManual] = useState(false);
  const done = () => { reload(); onChange(); };

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <FilterTabs value={status} onChange={setStatus} options={["pending", "awaiting_txid", "approved", "rejected", "all"]} testPrefix="dep-filter" />
        <button data-testid="manual-deposit-btn" onClick={() => setManual(true)} className="nk-btn-primary nk-btn-sm mb-5"><Plus size={14} />Add funds manually</button>
      </div>
      <ManualDeposit open={manual} onOpenChange={setManual} onDone={done} />
      {!list?.length ? <Empty testId="admin-deposits-empty" text="No deposit requests here." /> : (
        <div className="nk-card overflow-x-auto">
          <table className="nk-table" data-testid="admin-deposits-table">
            <thead><tr><th>Date</th><th>User</th><th>Ref</th><th>Coin</th><th>Expected</th><th>TXID</th><th>Status</th><th /></tr></thead>
            <tbody>{list.map((d) => (
              <tr key={d.id} data-testid={`admin-deposit-row-${d.id}`}>
                <td className="font-mono text-xs">{fmtDate(d.created_at)}</td>
                <td className="text-xs">{d.user_email}</td>
                <td className="font-mono text-xs">{d.reference}</td>
                <td className="text-xs">{COIN_LABEL[d.coin] || "Other"}{d.manual && <div className="font-mono text-[10px] uppercase text-[#22D3EE]" title={d.note}>manual · {d.reviewed_by}</div>}</td>
                <td className="font-mono text-[#22C55E]">{money(d.amount_cents)}{d.credited_cents != null && d.credited_cents !== d.amount_cents && <div className="text-xs text-[#4ADE80]">credited {money(d.credited_cents)}</div>}</td>
                <td className="max-w-[180px] truncate font-mono text-xs" title={d.txid}>{d.txid || "-"}</td>
                <td><StatusBadge status={d.status} />{d.reason && <div className="mt-1 text-xs text-[#FF2A5F]">{d.reason}</div>}</td>
                <td className="whitespace-nowrap text-right">
                  {d.status === "pending" && <button data-testid={`dep-approve-${d.id}`} onClick={() => setApprove(d)} className="nk-btn-primary nk-btn-sm mr-2">Approve</button>}
                  {["pending", "awaiting_txid"].includes(d.status) && <button data-testid={`dep-reject-${d.id}`} onClick={() => setReject(d)} className="nk-btn-danger nk-btn-sm">Reject</button>}
                </td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
      <PromptDialog testId="dep-approve" open={!!approve} onOpenChange={(o) => !o && setApprove(null)} title="Approve deposit"
        description={approve && `Verify TXID ${approve.txid} on-chain before crediting. Adjust amount if the received value differs.`}
        label="Amount to credit (USD)" type="number" defaultValue={approve ? (approve.amount_cents / 100).toFixed(2) : ""} confirmText="Credit wallet"
        onSubmit={async (v) => { try { await api.post(`/admin/deposits/${approve.id}/approve`, { amount: parseFloat(v) }); toast.success("Wallet credited"); done(); } catch (e) { toast.error(errMsg(e)); throw e; } }} />
      <PromptDialog testId="dep-reject" open={!!reject} onOpenChange={(o) => !o && setReject(null)} title="Reject deposit" label="Reason" danger confirmText="Reject"
        onSubmit={async (v) => { try { await api.post(`/admin/deposits/${reject.id}/reject`, { reason: v }); toast.success("Deposit rejected"); done(); } catch (e) { toast.error(errMsg(e)); throw e; } }} />
    </div>
  );
}
