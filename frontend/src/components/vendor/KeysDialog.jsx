import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Trash2 } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { StatusBadge } from "@/components/Shared";

export function KeysDialog({ product, onOpenChange, onChanged }) {
  const [keys, setKeys] = useState([]);
  const [text, setText] = useState("");
  const load = () => product && api.get(`/vendor/products/${product.id}/keys`).then((r) => setKeys(r.data));
  useEffect(() => { load(); setText(""); }, [product]); // eslint-disable-line

  const add = async () => {
    try {
      const { data } = await api.post(`/vendor/products/${product.id}/keys`, { keys: text });
      toast.success(`${data.added} keys added${data.skipped ? `, ${data.skipped} duplicates skipped` : ""}`);
      setText(""); load(); onChanged();
    } catch (e) { toast.error(errMsg(e)); }
  };
  const del = async (id) => {
    try { await api.delete(`/vendor/keys/${id}`); load(); onChanged(); } catch (e) { toast.error(errMsg(e)); }
  };
  const avail = keys.filter((k) => k.status === "available").length;

  return (
    <Dialog open={!!product} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto border-line bg-surface sm:max-w-xl" data-testid="keys-dialog">
        <DialogHeader><DialogTitle className="font-display">Key stock · {product?.title}</DialogTitle></DialogHeader>
        <div>
          <label className="nk-label">Add keys (one per line)</label>
          <textarea data-testid="keys-textarea" className="nk-input min-h-[110px] font-mono text-xs" placeholder={"XXXX-XXXX-XXXX\nYYYY-YYYY-YYYY"} value={text} onChange={(e) => setText(e.target.value)} />
          <button data-testid="keys-add-btn" disabled={!text.trim()} onClick={add} className="nk-btn-primary nk-btn-sm mt-2">Add to stock</button>
        </div>
        <div className="font-mono text-xs text-slate-400" data-testid="keys-available-count">{avail} available · {keys.length - avail} sold</div>
        <div className="max-h-64 space-y-1 overflow-y-auto">
          {keys.map((k) => (
            <div key={k.id} className="flex items-center gap-2 rounded-md border border-line bg-deep px-3 py-2">
              <code className="min-w-0 flex-1 truncate text-xs">{k.key}</code>
              <StatusBadge status={k.status} />
              {k.status === "available" && <button data-testid={`key-delete-${k.id}`} onClick={() => del(k.id)} className="text-slate-500 hover:text-[#FF2A5F]"><Trash2 size={14} /></button>}
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
