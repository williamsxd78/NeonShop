import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { Store, KeyRound, Wallet, ShoppingBag, LayoutGrid, Bell, Shield, Boxes, LogOut, Plus, Home, BadgeCheck, User } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { money } from "@/lib/api";
import { ChatButton } from "@/components/ChatButton";
import { GuestGate } from "@/components/GuestGate";
import { BrandName, BrandMark } from "@/components/Brand";
import { useSite } from "@/lib/site";

const navCls = ({ isActive }) =>
  `flex items-center gap-2 rounded-full px-3.5 py-2 text-sm font-medium transition-colors ${isActive ? "bg-brand/10 text-brand" : "text-slate-400 hover:text-white"}`;

function TopNav() {
  const { user, signOut } = useAuth();
  const nav = useNavigate();
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-ink/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4 sm:px-6 lg:px-8">
        <Link to="/" data-testid="brand-logo" className="flex items-center gap-2">
          <BrandMark />
          <BrandName className="text-lg font-bold" />
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
              <Link to="/wallet" data-testid="header-balance" className="hidden items-center gap-2 rounded-full border border-line bg-surface py-1 pl-3 pr-1 sm:flex">
                <span className="font-mono text-sm text-brandlt">{money(user.balance_cents)}</span>
                <span className="grid h-7 w-7 place-items-center rounded-full bg-brand text-ink"><Plus size={14} /></span>
              </Link>
              <Link to="/notifications" data-testid="header-notifications" className="relative grid h-11 w-11 place-items-center rounded-xl border border-line bg-surface text-slate-300 hover:text-white">
                <Bell size={18} />
                {user.unread_notifications > 0 && <span data-testid="notif-badge" className="absolute right-1.5 top-1.5 grid h-4 min-w-4 place-items-center rounded-full bg-[#FF2A5F] px-1 text-[10px] font-bold text-white">{user.unread_notifications}</span>}
              </Link>
              <Link to="/account" data-testid="header-account" className="grid h-11 w-11 place-items-center rounded-full border border-line bg-[#1C1F1E] text-slate-300 hover:text-white" title={user.name}><User size={18} /></Link>
              <button data-testid="logout-btn" onClick={() => { signOut(); nav("/login"); }} className="hidden h-10 w-10 place-items-center rounded-full text-slate-400 hover:text-[#FF2A5F] md:grid"><LogOut size={17} /></button>
            </>
          ) : (
            <>
              <Link to="/login" data-guest-allow data-testid="header-login" className="nk-btn-ghost nk-btn-sm">Log in</Link>
              <Link to="/register" data-guest-allow data-testid="header-register" className="nk-btn-primary nk-btn-sm">Sign up</Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

const bCls = ({ isActive }) => `flex flex-col items-center gap-1 px-2 py-1 text-[11px] font-medium ${isActive ? "text-brand" : "text-slate-500"}`;

function BottomNav() {
  return (
    <nav data-testid="bottom-nav" className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-around border-t border-line bg-surface/95 px-2 py-2 backdrop-blur-lg md:hidden">
      <NavLink to="/" end className={bCls} data-testid="bnav-market"><Home size={22} />Shop</NavLink>
      <NavLink to="/vault" className={bCls} data-testid="bnav-vault"><KeyRound size={22} />Vault</NavLink>
      <NavLink to="/account" className={bCls} data-testid="bnav-menu"><LayoutGrid size={22} />More</NavLink>
      <NavLink to="/wallet" className={bCls} data-testid="bnav-wallet"><Wallet size={22} />Wallet</NavLink>
      <NavLink to="/vendors" className={bCls} data-testid="bnav-vendors"><BadgeCheck size={22} />Vendors</NavLink>
    </nav>
  );
}

const FLink = ({ l }) => (l.url.startsWith("/")
  ? <Link to={l.url} className="text-sm text-slate-400 hover:text-white">{l.label}</Link>
  : <a href={l.url} target="_blank" rel="noopener noreferrer" className="text-sm text-slate-400 hover:text-white">{l.label}</a>);

function SiteFooter() {
  const { footer } = useSite();
  const cols = footer?.columns || [];
  return (
    <footer className="relative z-10 mb-20 border-t border-line md:mb-0" data-testid="site-footer">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className={`flex flex-wrap gap-8 ${cols.length ? "md:justify-between" : "justify-center"}`}>
            <div className="min-w-[180px]">
              <Link to="/" className="flex items-center gap-2"><BrandMark size={15} className="h-8 w-8" /><BrandName className="text-lg font-bold" /></Link>
            </div>
            {cols.map((c, i) => (
              <div key={i} className="min-w-[130px]" data-testid={`footer-col-${i}`}>
                {c.title && <div className="nk-label mb-3">{c.title}</div>}
                <div className="flex flex-col gap-2">{c.links.map((l, j) => <FLink key={j} l={l} />)}</div>
              </div>
            ))}
        </div>
        {footer?.text && <p className="mt-8 border-t border-line pt-5 text-center font-mono text-xs text-slate-600" data-testid="footer-text">{footer.text}</p>}
      </div>
    </footer>
  );
}

export default function Layout() {
  return (
    <div className="grain min-h-screen">
      <TopNav />
      <main className="relative z-10 mx-auto max-w-7xl px-4 pb-28 pt-6 sm:px-6 md:pb-16 lg:px-8">
        <Outlet />
      </main>
      <SiteFooter />
      <ChatButton />
      <GuestGate />
      <BottomNav />
    </div>
  );
}
