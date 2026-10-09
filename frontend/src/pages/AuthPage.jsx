import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { Zap, ShoppingCart, Boxes, Mail, Lock, Eye, EyeOff, User, Store, ArrowLeft, LogIn, UserPlus, ArrowRight } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useCaptcha, CaptchaField } from "@/components/Captcha";

const Field = ({ label, icon: Icon, right, children }) => (
  <div>
    <div className="mb-2 flex items-center justify-between"><label className="font-display text-sm font-semibold text-slate-200">{label}</label>{right}</div>
    <div className="relative">
      <Icon size={18} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
      {children}
    </div>
  </div>
);
const inp = "nk-input h-12 rounded-xl bg-[#0E100F] pl-11 text-[15px]";

export default function AuthPage({ mode }) {
  const isLogin = mode === "login";
  const { user, signIn } = useAuth();
  const nav = useNavigate();
  const [f, setF] = useState({ email: "", password: "", confirm: "", name: "", role: "buyer", store_name: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [show, setShow] = useState(false);
  const cap = useCaptcha();
  if (user) return <Navigate to={user.role === "admin" ? "/admin" : user.role === "vendor" ? "/vendor" : "/"} replace />;

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    if (!isLogin && f.password !== f.confirm) return setErr("Passwords do not match");
    setBusy(true);
    try {
      const { confirm, ...rest } = f;
      const body = { ...(isLogin ? { email: f.email, password: f.password } : rest), ...cap.payload };
      const { data } = await api.post(isLogin ? "/auth/login" : "/auth/register", body);
      signIn(data.token, data.user);
      nav(data.user.role === "admin" ? "/admin" : data.user.role === "vendor" ? "/vendor" : "/");
    } catch (e2) { setErr(errMsg(e2)); cap.reload(); } finally { setBusy(false); }
  };
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const eye = (
    <button type="button" data-testid={`${mode}-toggle-password`} onClick={() => setShow(!show)} className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white">
      {show ? <EyeOff size={18} /> : <Eye size={18} />}
    </button>
  );

  return (
    <div className="grain relative min-h-screen overflow-hidden px-4 py-10">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[420px] bg-[radial-gradient(ellipse_at_top,rgba(34,197,94,0.14),transparent_65%)]" />
      <div className="relative z-10 mx-auto w-full max-w-md nk-rise">
        <Link to="/" data-testid="auth-brand" className="mb-3 flex items-center justify-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-xl text-[#4ADE80] drop-shadow-[0_0_12px_rgba(34,197,94,0.6)]"><Zap size={30} /></span>
          <span className="font-display text-4xl font-bold tracking-tight">Neon<span className="text-[#4ADE80]">Keys</span></span>
        </Link>
        <p className="mb-8 text-center font-display text-lg text-slate-400">{isLogin ? "Secure access portal" : "Create your account"}</p>

        <form onSubmit={submit} data-testid={`${mode}-form`} className="space-y-5 rounded-3xl border border-[#272B29] bg-[#161918]/90 p-6 shadow-[0_20px_60px_rgba(0,0,0,0.45)] sm:p-8">
          {!isLogin && <Link to="/login" data-testid="register-back-link" className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"><ArrowLeft size={16} />Back</Link>}
          {!isLogin && (
            <div className="grid grid-cols-2 gap-2">
              {[["buyer", "Buyer", ShoppingCart], ["vendor", "Vendor", Boxes]].map(([r, l, Icon]) => (
                <button type="button" key={r} data-testid={`register-role-${r}`} onClick={() => setF({ ...f, role: r })}
                  className={`flex h-12 items-center justify-center gap-2 rounded-xl border text-sm font-semibold transition-colors ${f.role === r ? "border-[#22C55E]/60 bg-[#22C55E]/10 text-[#4ADE80]" : "border-[#272B29] bg-[#0E100F] text-slate-400"}`}>
                  <Icon size={16} />{l}
                </button>
              ))}
            </div>
          )}
          {!isLogin && <Field label="Name" icon={User}><input data-testid="register-name-input" className={inp} required placeholder="Your name" value={f.name} onChange={set("name")} /></Field>}
          {!isLogin && f.role === "vendor" && <Field label="Store name" icon={Store}><input data-testid="register-store-input" className={inp} placeholder="Your store name" value={f.store_name} onChange={set("store_name")} /></Field>}
          <Field label="Email" icon={Mail}><input data-testid={`${mode}-email-input`} className={inp} type="email" required placeholder="Enter your email" value={f.email} onChange={set("email")} /></Field>
          <Field label="Password" icon={Lock}>
            <input data-testid={`${mode}-password-input`} className={`${inp} pr-12`} type={show ? "text" : "password"} required minLength={6} placeholder={isLogin ? "Enter your password" : "Create a password"} value={f.password} onChange={set("password")} />
            {eye}
          </Field>
          {!isLogin && <Field label="Confirm password" icon={Lock}><input data-testid="register-confirm-input" className={inp} type={show ? "text" : "password"} required minLength={6} placeholder="Confirm your password" value={f.confirm} onChange={set("confirm")} /></Field>}
          <CaptchaField cap={cap} testPrefix={mode} />
          {!isLogin && f.role === "vendor" && <p className="text-xs text-[#FFB800]">Vendor accounts require admin approval before listing products.</p>}
          {err && <p data-testid={`${mode}-error`} className="rounded-lg border border-[#FF2A5F]/30 bg-[#FF2A5F]/10 px-3 py-2 text-sm text-[#FF6B8B]">{err}</p>}
          <button data-testid={`${mode}-submit-button`} disabled={busy}
            className="flex h-14 w-full items-center justify-center gap-3 rounded-xl bg-gradient-to-r from-[#22C55E] to-[#10B981] font-display text-lg font-semibold text-[#06140C] shadow-[0_8px_30px_rgba(34,197,94,0.25)] transition-transform active:scale-[0.98] disabled:opacity-60">
            {isLogin ? <LogIn size={20} /> : <UserPlus size={20} />}{busy ? "Please wait…" : isLogin ? "Sign in" : "Create account"}
          </button>
          <p className="text-center text-[15px] text-slate-400">
            {isLogin ? "Don't have an account? " : "Already have an account? "}
            <Link data-testid={`${mode}-switch-link`} to={isLogin ? "/register" : "/login"} className="inline-flex items-center gap-1 font-semibold text-[#4ADE80] hover:underline">
              {isLogin ? <>Create account <ArrowRight size={15} /></> : "Sign in"}
            </Link>
          </p>
        </form>
        <p className="mt-6 text-center font-mono text-xs text-slate-600">NeonKeys · {isLogin ? "Secure auth" : "Secure registration"}</p>
      </div>
    </div>
  );
}
