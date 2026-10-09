import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { Store, KeyRound, Wallet, ShoppingBag, LayoutGrid, Bell, Shield, Boxes, LogOut, Plus, Zap, Home, BadgeCheck, User } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { money } from "@/lib/api";
import { ChatButton } from "@/components/ChatButton";

const navCls = ({ isActive }) =>
  `flex items-center gap-2 rounded-full px-3.5 py-2 text-sm font-medium transition-colors ${isActive ? "bg-[#22C55E]/10 text-[#22C55E]" : "text-slate-400 hover:text-white"}`;

function TopNav() {
  const { user, signOut } = useAuth();
  const nav = useNavigate();
  return (
    <header className="sticky top-0 z-40 border-b border-[#272B29] bg-[#0A0B0B]/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4 sm:px-6 lg:px-8">
        <Link to="/" data-testid="brand-logo" className="flex items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-[#22C55E]/10 text-[#22C55E] shadow-[0_0_18px_rgba(34,197,94,0.35)]"><Zap size={18} /></span>
          <span className="font-display text-lg font-bold tracking-tight">Neon<span className="text-[#22C55E]">Keys</span></span>
        </Link>
        <nav className="ml-6 hidden items-center gap-1 md:flex">
          <NavLink to="/" end className={navCls} data-testid="nav-market"><Store size={16} />Shop</NavLink>
          <NavLink to="/vendors" className={navCls} data-testid="nav-vendors"><BadgeCheck size={16} />Vendors</NavLink>
          {user && <NavLink to="/vault" className={navCls} data-testid="nav-vault"><KeyRound size={16} />Vault</NavLink>}
          {user && <NavLink to="/orders" className={navCls} data-testid="nav-orders"><ShoppingBag size={16} />Orders</NavLink>}
          {user?.role === "vendor" && <NavLink to="/vendor" className={navCls} data-testid="nav-vendor"><Boxes size={16} />Vendor</NavLink>}
          {user?.role === "admin" && <NavLink to="/admin" className={navCls} data-testid="nav-admin"><Shield size={16} />Admin</NavLink>}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          {user ? (
            <>
              <Link to="/wallet" data-testid="header-balance" className="hidden items-center gap-2 rounded-full border border-[#272B29] bg-[#121413] py-1 pl-3 pr-1 sm:flex">
                <span className="font-mono text-sm text-[#4ADE80]">{money(user.balance_cents)}</span>
                <span className="grid h-7 w-7 place-items-center rounded-full bg-[#22C55E] text-[#0A0B0B]"><Plus size={14} /></span>
              </Link>
              <Link to="/notifications" data-testid="header-notifications" className="relative grid h-11 w-11 place-items-center rounded-xl border border-[#272B29] bg-[#121413] text-slate-300 hover:text-white">
                <Bell size={18} />
                {user.unread_notifications > 0 && <span data-testid="notif-badge" className="absolute right-1.5 top-1.5 grid h-4 min-w-4 place-items-center rounded-full bg-[#FF2A5F] px-1 text-[10px] font-bold text-white">{user.unread_notifications}</span>}
              </Link>
              <Link to="/account" data-testid="header-account" className="grid h-11 w-11 place-items-center rounded-full border border-[#272B29] bg-[#1C1F1E] text-slate-300 hover:text-white" title={user.name}><User size={18} /></Link>
              <button data-testid="logout-btn" onClick={() => { signOut(); nav("/login"); }} className="hidden h-10 w-10 place-items-center rounded-full text-slate-400 hover:text-[#FF2A5F] md:grid"><LogOut size={17} /></button>
            </>
          ) : (
            <>
              <Link to="/login" data-testid="header-login" className="nk-btn-ghost nk-btn-sm">Log in</Link>
              <Link to="/register" data-testid="header-register" className="nk-btn-primary nk-btn-sm">Sign up</Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

const bCls = ({ isActive }) => `flex flex-col items-center gap-1 px-2 py-1 text-[11px] font-medium ${isActive ? "text-[#22C55E]" : "text-slate-500"}`;

function BottomNav() {
  return (
    <nav data-testid="bottom-nav" className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-around border-t border-[#272B29] bg-[#121413]/95 px-2 py-2 backdrop-blur-lg md:hidden">
      <NavLink to="/" end className={bCls} data-testid="bnav-market"><Home size={22} />Shop</NavLink>
      <NavLink to="/vault" className={bCls} data-testid="bnav-vault"><KeyRound size={22} />Vault</NavLink>
      <NavLink to="/account" className={bCls} data-testid="bnav-menu"><LayoutGrid size={22} />More</NavLink>
      <NavLink to="/wallet" className={bCls} data-testid="bnav-wallet"><Wallet size={22} />Wallet</NavLink>
      <NavLink to="/vendors" className={bCls} data-testid="bnav-vendors"><BadgeCheck size={22} />Vendors</NavLink>
    </nav>
  );
}

export default function Layout() {
  return (
    <div className="grain min-h-screen">
      <TopNav />
      <main className="relative z-10 mx-auto max-w-7xl px-4 pb-28 pt-6 sm:px-6 md:pb-16 lg:px-8">
        <Outlet />
      </main>
      <footer className="relative z-10 mb-20 border-t border-[#272B29] py-6 text-center md:mb-0">
        <div className="font-display text-lg font-bold">Neon<span className="text-[#22C55E]">Keys</span></div>
        <p className="mt-1 font-mono text-xs text-slate-600">© 2026 NeonKeys · Verified vendors · Instant delivery</p>
      </footer>
      <ChatButton />
      <BottomNav />
    </div>
  );
}
