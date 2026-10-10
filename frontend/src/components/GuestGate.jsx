import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Lock } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useSite } from "@/lib/site";
import { AuthForm, homeFor } from "@/pages/AuthPage";
import { BrandName } from "@/components/Brand";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

const ALLOW = "[data-guest-allow], [role='dialog'], [data-radix-popper-content-wrapper]";

export function GuestGate() {
  const { user } = useAuth();
  const { guest_lock } = useSite();
  const loc = useLocation();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState("login");
  const next = useRef(null);
  const locked = guest_lock && user === false;

  const openRef = useRef(false);
  openRef.current = open;

  useEffect(() => {
    if (!locked) return undefined;
    const allowed = (e) => e.target.closest?.(ALLOW);
    const block = (e) => {
      if (allowed(e)) return;
      e.preventDefault();
      e.stopPropagation();
      if (e.type !== "click" || openRef.current) return;
      const a = e.target.closest?.("a[href]");
      next.current = a && a.origin === window.location.origin ? a.pathname + a.search : null;
      setMode("login");
      setOpen(true);
    };
    const unfocus = (e) => { if (!allowed(e)) e.target.blur?.(); };
    const types = ["click", "pointerdown", "submit"];
    types.forEach((t) => document.addEventListener(t, block, true));
    document.addEventListener("focusin", unfocus, true);
    return () => {
      types.forEach((t) => document.removeEventListener(t, block, true));
      document.removeEventListener("focusin", unfocus, true);
    };
  }, [locked]);

  const deep = locked && loc.pathname !== "/";
  useEffect(() => {
    if (!deep) return;
    next.current = loc.pathname + loc.search;
    nav("/", { replace: true });
    setMode("login");
    setOpen(true);
  }, [deep]); // eslint-disable-line

  if (!locked && !open) return null;

  const done = (u) => { setOpen(false); nav(next.current || (u.role === "buyer" ? loc.pathname : homeFor(u))); next.current = null; };
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-h-[92vh] overflow-y-auto border-line bg-deep p-4 sm:max-w-md sm:p-6" data-testid="guest-gate-dialog">
        <DialogHeader className="items-center text-center">
          <span className="mb-1 grid h-11 w-11 place-items-center rounded-full border border-brand/30 bg-brand/10 text-brandlt"><Lock size={18} /></span>
          <DialogTitle className="font-display text-xl">{mode === "login" ? <>Sign in to <BrandName className="inline" /></> : "Create your free account"}</DialogTitle>
          <DialogDescription>{mode === "login" ? "Log in or sign up to browse products, vendors and deals." : "Takes less than a minute. Then you're straight back where you were."}</DialogDescription>
        </DialogHeader>
        <AuthForm key={mode} mode={mode} testPrefix="gate-" onDone={done} onSwitch={() => setMode(mode === "login" ? "register" : "login")} />
      </DialogContent>
    </Dialog>
  );
}
