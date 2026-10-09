import { useState } from "react";
import { toast } from "sonner";
import { api, errMsg, money, fmtDate } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { StatusBadge, Empty, FilterTabs, PromptDialog } from "@/components/Shared";

export function AdminVendors({ onChange, globalPct }) {
  const [status, setStatus] = useState("pending");
  const [list, reload] = useFetch("/admin/vendors", { status });
  const [reject, setReject] = useState(null);
  const [comm, setComm] = useState(null);
  const done = () => { reload(); onChange(); };
  const approve = async (v) => { try { await api.post(`/admin/vendors/${v.id}/approve`); toast.success("Vendor approved"); done(); } catch (e) { toast.error(errMsg(e)); } };

  return (
    <div>
      <FilterTabs value={status} onChange={setStatus} options={["pending", "approved", "rejected", "all"]} testPrefix="vendor-filter" />
      {!list?.length ? <Empty testId="admin-vendors-empty" text="No vendors here." /> : (
        <div className="nk-card overflow-x-auto">
          <table className="nk-table" data-testid="admin-vendors-table">
            <thead><tr><th>Joined</th><th>Store</th><th>Email</th><th>Earnings</th><th>Commission</th><th>Status</th><th /></tr></thead>
            <tbody>{list.map((v) => (
              <tr key={v.id} data-testid={`admin-vendor-row-${v.id}`}>
                <td className="font-mono text-xs">{fmtDate(v.created_at)}</td>
                <td className="font-medium text-slate-100">{v.store_name}</td>
                <td className="text-xs">{v.email}</td>
                <td className="font-mono">{money(v.earnings_cents)}</td>
                <td className="font-mono text-xs">{v.commission_pct != null ? <span className="text-[#FFB800]">{v.commission_pct}% custom</span> : <span className="text-slate-500">{globalPct}% global</span>}</td>
                <td><StatusBadge status={v.vendor_status} /></td>
                <td className="whitespace-nowrap text-right">
                  {v.vendor_status !== "approved" && <button data-testid={`vendor-approve-${v.id}`} onClick={() => approve(v)} className="nk-btn-primary nk-btn-sm mr-2">Approve</button>}
                  {v.vendor_status === "pending" && <button data-testid={`vendor-reject-${v.id}`} onClick={() => setReject(v)} className="nk-btn-danger nk-btn-sm mr-2">Reject</button>}
                  <button data-testid={`vendor-commission-${v.id}`} onClick={() => setComm(v)} className="nk-btn-ghost nk-btn-sm">Set %</button>
                </td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
      <PromptDialog testId="vendor-reject" open={!!reject} onOpenChange={(o) => !o && setReject(null)} title="Reject vendor" label="Reason" danger confirmText="Reject"
        onSubmit={async (v) => { try { await api.post(`/admin/vendors/${reject.id}/reject`, { reason: v }); toast.success("Vendor rejected"); done(); } catch (e) { toast.error(errMsg(e)); throw e; } }} />
      <PromptDialog testId="vendor-comm" open={!!comm} onOpenChange={(o) => !o && setComm(null)} title={`Commission for ${comm?.store_name || ""}`} required={false}
        description={`Leave empty to use the global default (${globalPct}%).`} label="Custom commission %" type="number"
        defaultValue={comm?.commission_pct != null ? String(comm.commission_pct) : ""} confirmText="Save"
        onSubmit={async (v) => { try { await api.put(`/admin/vendors/${comm.id}/commission`, { pct: v === "" ? null : parseFloat(v) }); toast.success("Commission updated"); done(); } catch (e) { toast.error(errMsg(e)); throw e; } }} />
    </div>
  );
}
