import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { Mail, Lock, Eye, EyeOff, User, Store, ArrowLeft, LogIn, UserPlus, ArrowRight } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useCaptcha, CaptchaField } from "@/components/Captcha";
import { BrandName, useBrand } from "@/components/Brand";
import { CategoryIcon } from "@/components/CategoryIcon";

const Field = ({ label, icon: Icon, right, children }) => (
  <div>
    <div className="mb-2 flex items-center justify-between"><label className="font-display text-sm font-semibold text-slate-200">{label}</label>{right}</div>
    <div className="relative">
      <Icon size={18} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
      {children}
    </div>
  </div>
);
const inp = "nk-input h-12 rounded-xl bg-deep pl-11 text-[15px]";

export function AuthForm({ mode, vendor = false, onDone, onSwitch, testPrefix = "" }) {
  const isLogin = mode === "login";
  const { signIn } = useAuth();
  const [f, setF] = useState({ email: "", password: "", confirm: "", name: "", store_name: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [show, setShow] = useState(false);
  const cap = useCaptcha();
  const tid = `${testPrefix}${mode}`;

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    if (!isLogin && f.password !== f.confirm) return setErr("Passwords do not match");
    setBusy(true);
    try {
      const { confirm, ...rest } = f;
      const body = { ...(isLogin ? { email: f.email, password: f.password } : { ...rest, role: vendor ? "vendor" : "buyer" }), ...cap.payload };
      const { data } = await api.post(isLogin ? "/auth/login" : "/auth/register", body);
      signIn(data.token, data.user);
      onDone(data.user);
    } catch (e2) { setErr(errMsg(e2)); cap.reload(); } finally { setBusy(false); }
  };
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const swTo = `${vendor ? "/vendor" : ""}${isLogin ? "/register" : "/login"}`;
  const Sw = ({ children, ...p }) => onSwitch ? <button type="button" onClick={onSwitch} {...p}>{children}</button> : <Link to={isLogin ? swTo : `${vendor ? "/vendor" : ""}/login`} {...p}>{children}</Link>;
  const eye = (
    <button type="button" data-testid={`${tid}-toggle-password`} onClick={() => setShow(!show)} className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white">
      {show ? <EyeOff size={18} /> : <Eye size={18} />}
    </button>
  );

  return (
    <form onSubmit={submit} data-testid={`${tid}-form`} className="space-y-5 rounded-3xl border border-line bg-[#161918]/90 p-6 shadow-[0_20px_60px_rgba(0,0,0,0.45)] sm:p-8">
      {!isLogin && <Sw data-testid={`${testPrefix}register-back-link`} className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"><ArrowLeft size={16} />Back</Sw>}
      {!isLogin && <Field label="Name" icon={User}><input data-testid={`${testPrefix}register-name-input`} className={inp} required placeholder="Your name" value={f.name} onChange={set("name")} /></Field>}
      {!isLogin && vendor && <Field label="Store name" icon={Store}><input data-testid="register-store-input" className={inp} required placeholder="Your store name" value={f.store_name} onChange={set("store_name")} /></Field>}
      <Field label="Email" icon={Mail}><input data-testid={`${tid}-email-input`} className={inp} type="email" required placeholder="Enter your email" value={f.email} onChange={set("email")} /></Field>
      <Field label="Password" icon={Lock}>
        <input data-testid={`${tid}-password-input`} className={`${inp} pr-12`} type={show ? "text" : "password"} required minLength={6} placeholder={isLogin ? "Enter your password" : "Create a password"} value={f.password} onChange={set("password")} />
        {eye}
      </Field>
      {!isLogin && <Field label="Confirm password" icon={Lock}><input data-testid={`${testPrefix}register-confirm-input`} className={inp} type={show ? "text" : "password"} required minLength={6} placeholder="Confirm your password" value={f.confirm} onChange={set("confirm")} /></Field>}
      <CaptchaField cap={cap} testPrefix={tid} />
      {!isLogin && vendor && <p className="text-xs text-[#FFB800]">Vendor accounts require admin approval before listing products.</p>}
      {err && <p data-testid={`${tid}-error`} className="rounded-lg border border-[#FF2A5F]/30 bg-[#FF2A5F]/10 px-3 py-2 text-sm text-[#FF6B8B]">{err}</p>}
      <button data-testid={`${tid}-submit-button`} disabled={busy}
        className="flex h-12 w-full items-center justify-center gap-3 rounded-xl bg-gradient-to-r from-brand to-brand/75 font-display text-base font-semibold text-[#06140C] shadow-[0_8px_30px_rgb(var(--nk-brand)/0.25)] transition-transform active:scale-[0.98] disabled:opacity-60">
        {isLogin ? <LogIn size={20} /> : <UserPlus size={20} />}{busy ? "Please wait…" : isLogin ? "Sign in" : "Create account"}
      </button>
      <p className="text-center text-[15px] text-slate-400">
        {isLogin ? "Don't have an account? " : "Already have an account? "}
        <Sw data-testid={`${tid}-switch-link`} className="inline-flex items-center gap-1 font-semibold text-brandlt hover:underline">
          {isLogin ? <>Create account <ArrowRight size={15} /></> : "Sign in"}
        </Sw>
      </p>
    </form>
  );
}

export const homeFor = (u) => (u.role === "admin" ? "/admin" : u.role === "vendor" ? "/vendor" : "/");

export default function AuthPage({ mode, vendor = false }) {
  const brand = useBrand();
  const isLogin = mode === "login";
  const { user } = useAuth();
  const nav = useNavigate();
  if (user) return <Navigate to={homeFor(user)} replace />;

  return (
    <div className="grain relative min-h-screen overflow-hidden px-4 py-10">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[420px] bg-[radial-gradient(ellipse_at_top,rgb(var(--nk-brand)/0.14),transparent_65%)]" />
      <div className="relative z-10 mx-auto w-full max-w-md nk-rise">
        <Link to="/" data-testid="auth-brand" className="mb-3 flex items-center justify-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-xl text-brandlt drop-shadow-[0_0_12px_rgb(var(--nk-brand)/0.6)]"><CategoryIcon name={brand.icon} size={30} /></span>
          <BrandName className="text-3xl font-semibold" />
        </Link>
        {vendor && <div className="mb-2 flex justify-center"><span data-testid="vendor-portal-badge" className="inline-flex items-center gap-1.5 rounded-full border border-brand/30 bg-brand/10 px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-brandlt"><Store size={12} />Vendor portal</span></div>}
        <p className="mb-8 text-center font-display text-lg text-slate-400">{vendor ? (isLogin ? "Sign in to manage your store" : "Open your vendor store") : isLogin ? "Secure access portal" : "Create your account"}</p>

        <AuthForm key={`${mode}-${vendor}`} mode={mode} vendor={vendor} onDone={(u) => nav(homeFor(u))} />
        <p className="mt-6 text-center text-sm text-slate-400" data-testid="portal-switch">
          {vendor ? <>Not a vendor? <Link data-testid="buyer-portal-link" to={isLogin ? "/login" : "/register"} className="font-semibold text-brandlt hover:underline">Buyer {isLogin ? "login" : "sign up"}</Link></>
            : <>Are you a vendor? <Link data-testid="vendor-portal-link" to={isLogin ? "/vendor/login" : "/vendor/register"} className="inline-flex items-center gap-1 font-semibold text-brandlt hover:underline">Vendor {isLogin ? "login" : "sign up"} <ArrowRight size={14} /></Link></>}
        </p>
        <p className="mt-3 text-center font-mono text-xs text-slate-600">{brand.name_start}{brand.name_end} · {isLogin ? "Secure auth" : "Secure registration"}</p>
      </div>
    </div>
  );
}
