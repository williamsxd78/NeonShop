import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { User, Pencil, KeyRound, Wallet, Package, History, Bell, Boxes, Shield, BadgeCheck, LogOut, ChevronRight, ArrowLeft, Zap } from "lucide-react";
import { api, errMsg, money } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { StatusBadge, PromptDialog } from "@/components/Shared";

const Row = ({ to, title, sub, Icon, color }) => (
  <Link to={to} data-testid={`account-link-${to.slice(1) || "home"}`} className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-white/[0.02]">
    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg" style={{ background: `${color}1A`, color }}><Icon size={17} /></span>
    <div className="min-w-0 flex-1"><div className="font-display text-[15px] text-slate-100">{title}</div><div className="truncate text-xs text-slate-500">{sub}</div></div>
    <ChevronRight size={18} className="text-slate-600" />
  </Link>
);

export default function Account() {
  const { user, refresh, signOut } = useAuth();
  const nav = useNavigate();
  const [edit, setEdit] = useState(false);
  const rows = [
    ...(user.role === "admin" ? [["/admin", "Admin panel", "Queues, approvals, commission", Shield, "#FF2A5F"]] : []),
    ...(user.role === "vendor" ? [["/vendor", "Vendor dashboard", "Products, stock, sales, payouts", Boxes, "#22C55E"]] : []),
    ["/orders", "Orders", "Reopen marketplace deliveries", Package, "#22C55E"],
    ["/vault", "Key vault", "All your delivered license keys", KeyRound, "#A855F7"],
    ["/wallet", "Wallet", "Add funds with crypto", Wallet, "#FFB800"],
    ["/wallet", "Wallet transactions", "Deposits, purchases and credits", History, "#22D3EE"],
    ["/notifications", "Notifications", "Deposit approvals, deliveries, payouts", Bell, "#22D3EE"],
    ["/vendors", "Verified vendors", "Browse trusted sellers", BadgeCheck, "#4ADE80"],
  ];

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-8 flex items-center gap-4 nk-rise">
        <button onClick={() => nav(-1)} data-testid="account-back-btn" className="grid h-11 w-11 place-items-center rounded-xl border border-[#272B29] bg-[#171A19] text-slate-300"><ArrowLeft size={18} /></button>
        <h1 className="font-display text-2xl font-semibold">Account</h1>
        <Zap className="ml-auto text-[#22C55E]" size={22} />
      </div>
      <div className="mb-6 flex items-center gap-4">
        <div className="grid h-14 w-14 shrink-0 place-items-center rounded-full border-2 border-[#22C55E]/30 bg-[#171A19] text-slate-400"><User size={24} /></div>
        <div className="min-w-0 flex-1">
          <div data-testid="account-name" className="truncate font-display text-lg font-semibold">{user.name}</div>
          <div className="truncate text-sm text-slate-500">{user.email}</div>
          <div className="mt-1 flex gap-2"><StatusBadge status={user.role === "vendor" ? user.vendor_status : user.status} testId="account-vendor-status" /></div>
        </div>
        <Link to="/wallet" data-testid="account-balance" className="flex items-center gap-2 rounded-full border border-[#22C55E]/25 bg-[#22C55E]/10 px-3 py-1.5 font-mono text-sm text-[#4ADE80]"><Wallet size={14} />{money(user.balance_cents)}</Link>
      </div>
      <div className="mb-6 grid grid-cols-2 gap-3">
        <button data-testid="edit-profile-btn" onClick={() => setEdit(true)} className="flex items-center justify-center gap-2 rounded-xl border border-[#272B29] bg-[#171A19] py-2.5 text-sm hover:border-[#22C55E]/40"><Pencil size={14} />Edit profile</button>
        <Link to="/vault" data-testid="view-vault-btn" className="flex items-center justify-center gap-2 rounded-xl border border-[#272B29] bg-[#171A19] py-2.5 text-sm hover:border-[#22C55E]/40"><KeyRound size={14} />My keys</Link>
      </div>
      <div className="nk-card mb-6 divide-y divide-[#272B29] overflow-hidden rounded-2xl">
        {rows.map(([to, t, s, I, c]) => <Row key={t} to={to} title={t} sub={s} Icon={I} color={c} />)}
      </div>
      <button data-testid="account-logout-btn" onClick={() => { signOut(); nav("/login"); }} className="flex w-full items-center justify-center gap-2 rounded-2xl border border-[#FF2A5F]/20 bg-[#FF2A5F]/[0.06] py-3 text-sm text-[#FF2A5F] hover:bg-[#FF2A5F]/10"><LogOut size={16} />Sign out</button>
      <PromptDialog testId="profile-name" open={edit} onOpenChange={setEdit} title="Edit profile" label="Display name" defaultValue={user.name} confirmText="Save"
        onSubmit={async (v) => { try { await api.put("/auth/profile", { name: v }); toast.success("Profile updated"); refresh(); } catch (e) { toast.error(errMsg(e)); throw e; } }} />
    </div>
  );
}
