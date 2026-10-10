import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Eye, EyeOff } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export function ChangePasswordDialog({ open, onOpenChange }) {
  const blank = { current: "", next: "", confirm: "" };
  const [f, setF] = useState(blank);
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (open) { setF(blank); setShow(false); } }, [open]); // eslint-disable-line react-hooks/exhaustive-deps
  const mismatch = f.confirm && f.next !== f.confirm;
  const submit = async (e) => {
    e.preventDefault();
    if (f.next !== f.confirm) return toast.error("New passwords don't match");
    setBusy(true);
    try { await api.post("/auth/change-password", { current_password: f.current, new_password: f.next }); toast.success("Password changed"); onOpenChange(false); }
    catch (e2) { toast.error(errMsg(e2)); } finally { setBusy(false); }
  };
  const field = (k, label, testId, extra = {}) => (
    <div><label className="nk-label">{label}</label>
      <input data-testid={testId} type={show ? "text" : "password"} required className="nk-input" value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} {...extra} /></div>
  );
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-[#272B29] bg-[#0E100F] sm:max-w-md" data-testid="change-password-dialog">
        <DialogHeader><DialogTitle className="font-display">Change password</DialogTitle></DialogHeader>
        <form onSubmit={submit} className="space-y-3">
          {field("current", "Current password", "cp-current-input", { autoComplete: "current-password" })}
          {field("next", "New password (min 8 characters)", "cp-new-input", { minLength: 8, autoComplete: "new-password" })}
          {field("confirm", "Confirm new password", "cp-confirm-input", { minLength: 8, autoComplete: "new-password" })}
          {mismatch && <p className="text-xs text-[#FF2A5F]" data-testid="cp-mismatch">Passwords don't match</p>}
          <button type="button" data-testid="cp-toggle-show" onClick={() => setShow(!show)} className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white">
            {show ? <EyeOff size={13} /> : <Eye size={13} />}{show ? "Hide" : "Show"} passwords</button>
          <button data-testid="cp-submit" disabled={busy || mismatch} className="nk-btn-primary w-full">Update password</button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
