import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { Zap, ShoppingCart, Boxes } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export default function AuthPage({ mode }) {
  const isLogin = mode === "login";
  const { user, signIn } = useAuth();
  const nav = useNavigate();
  const [f, setF] = useState({ email: "", password: "", name: "", role: "buyer", store_name: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  if (user) return <Navigate to={user.role === "admin" ? "/admin" : user.role === "vendor" ? "/vendor" : "/"} replace />;

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      const body = isLogin ? { email: f.email, password: f.password } : f;
      const { data } = await api.post(isLogin ? "/auth/login" : "/auth/register", body);
      signIn(data.token, data.user);
      nav(data.user.role === "admin" ? "/admin" : data.user.role === "vendor" ? "/vendor" : "/");
    } catch (e2) { setErr(errMsg(e2)); } finally { setBusy(false); }
  };
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  return (
    <div className="grain grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden overflow-hidden lg:block">
        <img src="https://images.unsplash.com/photo-1705510144116-cc4d88838b14?w=1400&q=80" alt="" className="absolute inset-0 h-full w-full object-cover opacity-50" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0A0B0B] via-[#0A0B0B]/40 to-transparent" />
        <div className="absolute bottom-16 left-14 max-w-md">
          <div className="nk-eyebrow mb-4">B2B digital goods exchange</div>
          <h1 className="text-5xl font-extrabold leading-tight tracking-tight">Licenses delivered <span className="neon-text">the instant</span> you pay.</h1>
          <p className="mt-4 text-slate-400">Top up with crypto, buy from verified vendors, keep every key in one vault.</p>
        </div>
      </div>
      <div className="relative z-10 flex items-center justify-center px-5 py-12">
        <form onSubmit={submit} className="w-full max-w-sm space-y-5 nk-rise" data-testid={`${mode}-form`}>
          <Link to="/" className="mb-6 flex items-center gap-2">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-[#22C55E]/10 text-[#22C55E] shadow-[0_0_18px_rgba(34,197,94,0.35)]"><Zap size={18} /></span>
            <span className="font-display text-lg font-bold">Neon<span className="text-[#22C55E]">Keys</span></span>
          </Link>
          <h2 className="text-3xl font-bold tracking-tight">{isLogin ? "Welcome back" : "Create account"}</h2>
          {!isLogin && (
            <div className="grid grid-cols-2 gap-2">
              {[["buyer", "Buyer", ShoppingCart], ["vendor", "Vendor", Boxes]].map(([r, l, Icon]) => (
                <button type="button" key={r} data-testid={`register-role-${r}`} onClick={() => setF({ ...f, role: r })}
                  className={`flex items-center justify-center gap-2 rounded-lg border px-3 py-3 text-sm font-medium transition-colors ${f.role === r ? "border-[#22C55E]/60 bg-[#22C55E]/10 text-[#22C55E]" : "border-[#272B29] text-slate-400"}`}>
                  <Icon size={16} />{l}
                </button>
              ))}
            </div>
          )}
          {!isLogin && <div><label className="nk-label">Name</label><input data-testid="register-name-input" className="nk-input" required value={f.name} onChange={set("name")} /></div>}
          {!isLogin && f.role === "vendor" && <div><label className="nk-label">Store name</label><input data-testid="register-store-input" className="nk-input" value={f.store_name} onChange={set("store_name")} /></div>}
          <div><label className="nk-label">Email</label><input data-testid={`${mode}-email-input`} className="nk-input" type="email" required value={f.email} onChange={set("email")} /></div>
          <div><label className="nk-label">Password</label><input data-testid={`${mode}-password-input`} className="nk-input" type="password" required minLength={6} value={f.password} onChange={set("password")} /></div>
          {!isLogin && f.role === "vendor" && <p className="text-xs text-[#FFB800]">Vendor accounts require admin approval before listing products.</p>}
          {err && <p data-testid={`${mode}-error`} className="text-sm text-[#FF2A5F]">{err}</p>}
          <button data-testid={`${mode}-submit-button`} disabled={busy} className="nk-btn-primary w-full">{busy ? "Please wait…" : isLogin ? "Log in" : "Create account"}</button>
          <p className="text-center text-sm text-slate-500">
            {isLogin ? "New here? " : "Have an account? "}
            <Link data-testid={`${mode}-switch-link`} to={isLogin ? "/register" : "/login"} className="text-[#22C55E] hover:underline">{isLogin ? "Create an account" : "Log in"}</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
