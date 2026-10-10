import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Paperclip, X, Loader2 } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";

const cache = new Map();

export function TicketImage({ path, className = "h-20 w-20", removable, onRemove }) {
  const [src, setSrc] = useState(cache.get(path));
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (cache.has(path)) return;
    api.get(`/tickets/files/${path}`, { responseType: "blob" })
      .then((r) => { const u = URL.createObjectURL(r.data); cache.set(path, u); setSrc(u); })
      .catch(() => setSrc(null));
  }, [path]);
  const id = path.split("/").pop().split(".")[0].slice(0, 8);
  return (
    <div className={`relative shrink-0 overflow-hidden rounded-lg border border-[#272B29] bg-[#0A0B0B] ${className}`} data-testid={`ticket-attachment-${id}`}>
      {src ? <button type="button" onClick={() => setOpen(true)} className="h-full w-full"><img src={src} alt="attachment" className="h-full w-full object-cover" /></button>
        : <div className="grid h-full w-full place-items-center"><Loader2 size={14} className="animate-spin text-slate-600" /></div>}
      {removable && <button type="button" data-testid={`attachment-remove-${id}`} onClick={onRemove} className="absolute right-1 top-1 rounded-full bg-black/70 p-0.5 text-white"><X size={11} /></button>}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-3xl border-[#272B29] bg-[#0E100F] p-2" data-testid="attachment-viewer">
          <DialogTitle className="sr-only">Attachment</DialogTitle>
          {src && <img src={src} alt="attachment" className="max-h-[80vh] w-full rounded-md object-contain" />}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export function useAttachments() {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const add = async (list) => {
    const picked = [...list].slice(0, 4 - files.length);
    if (!picked.length) return toast.error("Max 4 screenshots per message");
    setUploading(true);
    try {
      for (const f of picked) {
        const fd = new FormData();
        fd.append("file", f);
        const { data } = await api.post("/tickets/upload", fd);
        setFiles((x) => [...x, data.path]);
      }
    } catch (e) { toast.error(errMsg(e)); } finally { setUploading(false); }
  };
  return { files, uploading, add, remove: (p) => setFiles((x) => x.filter((y) => y !== p)), clear: () => setFiles([]) };
}

export function AttachButton({ att, testId = "attach-btn" }) {
  const ref = useRef(null);
  return (
    <>
      <button type="button" data-testid={testId} onClick={() => ref.current?.click()} disabled={att.uploading || att.files.length >= 4}
        className="nk-btn-ghost h-11 w-11 shrink-0 !p-0" title="Attach screenshot">
        {att.uploading ? <Loader2 size={16} className="animate-spin" /> : <Paperclip size={16} />}
      </button>
      <input ref={ref} data-testid={`${testId}-input`} type="file" accept="image/png,image/jpeg,image/webp,image/gif" multiple className="hidden"
        onChange={(e) => { att.add(e.target.files); e.target.value = ""; }} />
    </>
  );
}

export function AttachPreview({ att }) {
  if (!att.files.length) return null;
  return (
    <div className="flex flex-wrap gap-2" data-testid="attach-preview">
      {att.files.map((p) => <TicketImage key={p} path={p} className="h-14 w-14" removable onRemove={() => att.remove(p)} />)}
    </div>
  );
}
