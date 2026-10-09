import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Plus, MessageCircle } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { PageHeader } from "@/components/Shared";
import { TicketList, TicketThread } from "@/components/support/TicketThread";

const TOPICS = ["General", "Deposit", "Order", "Vendor", "Account"];

function NewTicket({ onCreated, onCancel }) {
  const [f, setF] = useState({ subject: "", topic: "General", message: "" });
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try { const { data } = await api.post("/tickets", f); toast.success(`Ticket ${data.ref} created`); onCreated(data.id); }
    catch (e2) { toast.error(errMsg(e2)); } finally { setBusy(false); }
  };
  return (
    <form onSubmit={submit} className="nk-card space-y-4 p-5" data-testid="new-ticket-form">
      <div className="flex items-center gap-2"><MessageCircle size={16} className="text-[#4ADE80]" /><h3 className="font-display">New support request</h3></div>
      <div className="grid gap-3 sm:grid-cols-[1fr_160px]">
        <div><label className="nk-label">Subject</label><input data-testid="new-ticket-subject" required minLength={3} className="nk-input" placeholder="e.g. My deposit is not credited" value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })} /></div>
        <div><label className="nk-label">Topic</label>
          <select data-testid="new-ticket-topic" className="nk-input" value={f.topic} onChange={(e) => setF({ ...f, topic: e.target.value })}>{TOPICS.map((t) => <option key={t}>{t}</option>)}</select></div>
      </div>
      <div><label className="nk-label">Message</label><textarea data-testid="new-ticket-message" required className="nk-input min-h-[120px]" placeholder="Describe your issue. Include the deposit reference, TXID or order details if relevant."
        value={f.message} onChange={(e) => setF({ ...f, message: e.target.value })} /></div>
      <div className="flex justify-end gap-2">
        <button type="button" data-testid="new-ticket-cancel" onClick={onCancel} className="nk-btn-ghost nk-btn-sm">Cancel</button>
        <button data-testid="new-ticket-submit" disabled={busy} className="nk-btn-primary nk-btn-sm">Send request</button>
      </div>
    </form>
  );
}

export default function Support() {
  const [sp, setSp] = useSearchParams();
  const [list, reload] = useFetch("/tickets");
  const active = sp.get("t");
  const creating = sp.get("new") === "1" || (list && !list.length && !active);
  const pick = (id) => setSp({ t: id });
  return (
    <div>
      <PageHeader eyebrow="Help center" title="Support">
        <button data-testid="support-new-btn" onClick={() => setSp({ new: "1" })} className="nk-btn-primary nk-btn-sm"><Plus size={14} />New ticket</button>
      </PageHeader>
      <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
        <div className={active || creating ? "hidden lg:block" : ""}><TicketList items={list} active={active} onPick={pick} /></div>
        <div className={!active && !creating ? "hidden lg:block" : ""}>
          {creating ? <NewTicket onCreated={(id) => { reload(); pick(id); }} onCancel={() => setSp({})} />
            : active ? (
              <div>
                <button data-testid="support-back" onClick={() => setSp({})} className="mb-3 text-xs text-slate-400 hover:text-white lg:hidden">← All tickets</button>
                <TicketThread key={active} id={active} onChange={reload} />
              </div>
            ) : <div className="nk-card flex h-64 items-center justify-center text-sm text-slate-500">Select a ticket to view the conversation</div>}
        </div>
      </div>
    </div>
  );
}
