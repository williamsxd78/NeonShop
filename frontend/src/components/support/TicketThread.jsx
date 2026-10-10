import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Send, ShieldCheck, Lock, RotateCcw, CheckCircle2 } from "lucide-react";
import { api, errMsg, fmtDate } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { StatusBadge } from "@/components/Shared";
import { TicketImage, AttachButton, AttachPreview, useAttachments } from "@/components/support/Attachments";
import { QuickReplies } from "@/components/admin/CannedReplies";

export function TicketThread({ id, admin = false, onChange }) {
  const [t, reload] = useFetch(`/tickets/${id}`);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const att = useAttachments();
  const end = useRef(null);
  useEffect(() => { end.current?.scrollIntoView({ block: "nearest" }); }, [t?.messages?.length]);
  if (!t) return <div className="nk-card h-64 animate-pulse" />;

  const send = async (e) => {
    e.preventDefault();
    if (!msg.trim() && !att.files.length) return;
    setBusy(true);
    try { await api.post(`/tickets/${id}/messages`, { message: msg, attachments: att.files }); setMsg(""); att.clear(); await reload(); onChange?.(); }
    catch (e2) { toast.error(errMsg(e2)); } finally { setBusy(false); }
  };
  const setStatus = async (status) => {
    try { await api.post(`/admin/tickets/${id}/status`, { status }); toast.success(status === "closed" ? "Ticket closed" : "Ticket reopened"); await reload(); onChange?.(); }
    catch (e2) { toast.error(errMsg(e2)); }
  };
  const closed = t.status === "closed";

  return (
    <div className="nk-card flex flex-col" data-testid={`ticket-thread-${id}`}>
      <div className="flex flex-wrap items-start gap-3 border-b border-line p-4">
        <div className="min-w-0 flex-1">
          <div className="font-mono text-[10px] uppercase tracking-wider text-slate-500">{t.ref} · {t.topic}{t.order_id ? ` · order ${t.order_id.slice(0, 8)}` : ""}</div>
          <h3 className="truncate font-display text-base" data-testid="ticket-subject">{t.subject}</h3>
          {admin && <div className="text-xs text-slate-500">{t.user_name} · {t.user_email} · {t.user_role}</div>}
        </div>
        <StatusBadge status={t.status} testId="ticket-status" />
        {admin && (closed
          ? <button data-testid="ticket-reopen-btn" onClick={() => setStatus("open")} className="nk-btn-ghost nk-btn-sm"><RotateCcw size={13} />Reopen</button>
          : <button data-testid="ticket-close-btn" onClick={() => setStatus("closed")} className="nk-btn-ghost nk-btn-sm"><CheckCircle2 size={13} />Close</button>)}
      </div>
      <div className="max-h-[50vh] min-h-[200px] space-y-3 overflow-y-auto p-4" data-testid="ticket-messages">
        {t.messages.map((m) => {
          const mine = admin ? m.from_admin : !m.from_admin;
          return (
            <div key={m.id} className={`flex ${mine ? "justify-end" : "justify-start"}`} data-testid={`ticket-msg-${m.id}`}>
              <div className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm ${mine ? "rounded-br-sm bg-brand/15 text-slate-100" : "rounded-bl-sm border border-line bg-deep text-slate-200"}`}>
                <div className="mb-1 flex items-center gap-1.5 text-[10px] text-slate-500">
                  {m.from_admin && <ShieldCheck size={11} className="text-brandlt" />}{m.from_admin ? "Support team" : m.author_name} · {fmtDate(m.created_at)}
                </div>
                {m.message && <p className="whitespace-pre-wrap break-words">{m.message}</p>}
                {m.attachments?.length > 0 && <div className="mt-2 flex flex-wrap gap-2">{m.attachments.map((p) => <TicketImage key={p} path={p} />)}</div>}
              </div>
            </div>
          );
        })}
        <div ref={end} />
      </div>
      {closed && !admin ? (
        <div className="flex items-center gap-2 border-t border-line p-4 text-xs text-slate-500" data-testid="ticket-closed-note"><Lock size={13} />This ticket is closed. Open a new ticket if you need more help.</div>
      ) : (
        <form onSubmit={send} className="space-y-2 border-t border-line p-3">
          <AttachPreview att={att} />
          <div className="flex items-end gap-2">
          {admin && <QuickReplies ticket={t} onPick={(text) => setMsg((m) => (m.trim() ? `${m}\n\n${text}` : text))} />}
          <AttachButton att={att} testId="ticket-attach-btn" />
          <textarea data-testid="ticket-reply-input" rows={2} className="nk-input min-h-[44px] flex-1 resize-none" placeholder={admin ? "Reply to the user…" : "Write a message…"}
            value={msg} onChange={(e) => setMsg(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) send(e); }} />
          <button data-testid="ticket-reply-send" disabled={busy || att.uploading || (!msg.trim() && !att.files.length)} className="nk-btn-primary h-11 w-11 shrink-0 !p-0"><Send size={16} /></button>
          </div>
        </form>
      )}
    </div>
  );
}

export function TicketList({ items, active, onPick, admin = false }) {
  if (!items) return <div className="nk-card h-40 animate-pulse" />;
  if (!items.length) return <div className="nk-card p-6 text-center text-sm text-slate-500" data-testid="tickets-empty">No tickets yet.</div>;
  return (
    <div className="space-y-2" data-testid="tickets-list">
      {items.map((t) => {
        const unread = admin ? t.unread_admin : t.unread_user;
        return (
          <button key={t.id} data-testid={`ticket-row-${t.id}`} onClick={() => onPick(t.id)}
            className={`nk-card w-full p-3.5 text-left transition-colors ${active === t.id ? "border-brand/50 bg-brand/[0.06]" : "hover:border-brand/30"}`}>
            <div className="flex items-center gap-2">
              {unread && <span className="h-2 w-2 shrink-0 rounded-full bg-brand" data-testid={`ticket-unread-${t.id}`} />}
              <span className="min-w-0 flex-1 truncate text-sm text-slate-100">{t.subject}</span>
              <StatusBadge status={t.status} />
            </div>
            <div className="mt-1 truncate font-mono text-[10px] text-slate-500">{t.ref} · {t.topic}{admin ? ` · ${t.user_email}` : ""} · {fmtDate(t.updated_at)}</div>
          </button>
        );
      })}
    </div>
  );
}
