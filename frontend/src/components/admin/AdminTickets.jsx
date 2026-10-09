import { useState } from "react";
import { Search } from "lucide-react";
import { useFetch } from "@/lib/useFetch";
import { FilterTabs } from "@/components/Shared";
import { TicketList, TicketThread } from "@/components/support/TicketThread";

export function AdminTickets({ onChange }) {
  const [status, setStatus] = useState("open");
  const [q, setQ] = useState("");
  const [active, setActive] = useState(null);
  const [list, reload] = useFetch("/admin/tickets", { status, q });
  const changed = () => { reload(); onChange?.(); };
  return (
    <div>
      <div className="relative mb-4"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
        <input data-testid="admin-tickets-search" className="nk-input pl-9" placeholder="Search subject, email or TCK reference" value={q} onChange={(e) => setQ(e.target.value)} /></div>
      <FilterTabs value={status} onChange={(s) => { setStatus(s); setActive(null); }} options={["open", "answered", "closed", "all"]} testPrefix="tickets-filter" />
      <div className="grid gap-4 xl:grid-cols-[300px_1fr]">
        <div className={active ? "hidden xl:block" : ""}><TicketList items={list} active={active} onPick={(id) => { setActive(id); setTimeout(changed, 400); }} admin /></div>
        {active ? (
          <div>
            <button data-testid="admin-ticket-back" onClick={() => setActive(null)} className="mb-3 text-xs text-slate-400 hover:text-white xl:hidden">← All tickets</button>
            <TicketThread key={active} id={active} admin onChange={changed} />
          </div>
        ) : <div className="nk-card hidden h-64 items-center justify-center text-sm text-slate-500 xl:flex">Select a ticket to reply</div>}
      </div>
    </div>
  );
}
