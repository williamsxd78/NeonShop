import { useEffect, useState } from "react";
import { Bell } from "lucide-react";
import { api, fmtDate } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PageHeader, Empty } from "@/components/Shared";

export default function Notifications() {
  const { refresh } = useAuth();
  const [items, setItems] = useState(null);
  useEffect(() => {
    api.get("/notifications").then((r) => { setItems(r.data); api.post("/notifications/read-all").then(refresh); });
  }, []); // eslint-disable-line
  return (
    <div>
      <PageHeader eyebrow="Inbox" title="Notifications" />
      {items === null ? <div className="nk-card h-40 animate-pulse" /> : !items.length ? <Empty testId="notifications-empty" text="You're all caught up." /> : (
        <div className="space-y-3" data-testid="notifications-list">
          {items.map((n, i) => (
            <div key={n.id} className="nk-card nk-rise flex gap-4 p-4" style={{ animationDelay: `${i * 30}ms` }} data-testid={`notification-${n.id}`}>
              <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-full ${n.read ? "bg-[#272B29] text-slate-500" : "bg-[#22C55E]/10 text-[#22C55E]"}`}><Bell size={16} /></span>
              <div className="min-w-0">
                <div className="font-semibold">{n.title}</div>
                <p className="text-sm text-slate-400">{n.body}</p>
                <p className="mt-1 font-mono text-[11px] text-slate-600">{fmtDate(n.created_at)}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
