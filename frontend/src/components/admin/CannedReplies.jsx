import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Zap, Settings2, Plus, Trash2 } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

function ManageDialog({ open, onOpenChange, replies, onSaved }) {
  const [list, setList] = useState([]);
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (open) setList(replies.map((r) => ({ ...r }))); }, [open, replies]);
  const upd = (i, k, v) => setList(list.map((r, j) => (j === i ? { ...r, [k]: v } : r)));
  const save = async () => {
    setBusy(true);
    try { const { data } = await api.put("/admin/canned-replies", { replies: list.filter((r) => r.title.trim() && r.text.trim()) }); onSaved(data); toast.success("Quick replies saved"); onOpenChange(false); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto border-[#272B29] bg-[#0E100F] sm:max-w-2xl" data-testid="canned-manage-dialog">
        <DialogHeader><DialogTitle className="font-display">Quick replies</DialogTitle></DialogHeader>
        <p className="text-xs text-slate-500">Use <code className="text-[#4ADE80]">{"{name}"}</code> and <code className="text-[#4ADE80]">{"{ref}"}</code>; they're replaced with the user's name and ticket reference.</p>
        <div className="space-y-3">
          {list.map((r, i) => (
            <div key={i} className="space-y-2 rounded-lg border border-[#272B29] bg-[#121413] p-3" data-testid={`canned-row-${i}`}>
              <div className="flex gap-2">
                <input data-testid={`canned-title-${i}`} className="nk-input" placeholder="Title" value={r.title} onChange={(e) => upd(i, "title", e.target.value)} />
                <button data-testid={`canned-delete-${i}`} onClick={() => setList(list.filter((_, j) => j !== i))} className="nk-btn-ghost h-10 w-10 shrink-0 !p-0 text-[#FF2A5F]"><Trash2 size={14} /></button>
              </div>
              <textarea data-testid={`canned-text-${i}`} className="nk-input min-h-[80px]" placeholder="Reply text" value={r.text} onChange={(e) => upd(i, "text", e.target.value)} />
            </div>
          ))}
        </div>
        <div className="flex justify-between gap-2">
          <button data-testid="canned-add" onClick={() => setList([...list, { title: "", text: "" }])} disabled={list.length >= 30} className="nk-btn-ghost nk-btn-sm"><Plus size={14} />Add reply</button>
          <button data-testid="canned-save" onClick={save} disabled={busy} className="nk-btn-primary nk-btn-sm">Save</button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function QuickReplies({ ticket, onPick }) {
  const [replies, setReplies] = useState(null);
  const [manage, setManage] = useState(false);
  useEffect(() => { api.get("/admin/canned-replies").then((r) => setReplies(r.data)); }, []);
  const fill = (t) => t.replaceAll("{name}", ticket.user_name || "there").replaceAll("{ref}", ticket.ref);
  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button type="button" data-testid="quick-replies-btn" className="nk-btn-ghost h-11 w-11 shrink-0 !p-0" title="Quick replies"><Zap size={16} className="text-[#FFB800]" /></button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-72 border-[#272B29] bg-[#121413]" data-testid="quick-replies-menu">
          {(replies || []).map((r, i) => (
            <DropdownMenuItem key={i} data-testid={`quick-reply-${i}`} onSelect={() => onPick(fill(r.text))} className="flex-col items-start gap-0.5">
              <span className="text-sm text-slate-100">{r.title}</span>
              <span className="line-clamp-1 text-[11px] text-slate-500">{r.text}</span>
            </DropdownMenuItem>
          ))}
          {replies && !replies.length && <div className="px-2 py-3 text-xs text-slate-500">No quick replies yet.</div>}
          <DropdownMenuSeparator />
          <DropdownMenuItem data-testid="quick-replies-manage" onSelect={() => setManage(true)}><Settings2 size={14} className="mr-2" />Manage quick replies</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <ManageDialog open={manage} onOpenChange={setManage} replies={replies || []} onSaved={setReplies} />
    </>
  );
}
