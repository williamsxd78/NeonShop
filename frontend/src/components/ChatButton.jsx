import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { MessageCircle } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export function ChatButton() {
  const { user } = useAuth();
  const { pathname } = useLocation();
  const [unread, setUnread] = useState(0);
  useEffect(() => {
    if (!user || user.role === "admin") return;
    api.get("/tickets").then((r) => setUnread(r.data.filter((t) => t.unread_user).length)).catch(() => {});
  }, [user, pathname]);
  if (user?.role === "admin" || pathname.startsWith("/support")) return null;
  return (
    <Link to={user ? "/support?new=1" : "/login"} data-testid="live-chat-button" aria-label="Contact support"
      className="fixed bottom-24 right-4 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-[#22C55E] text-black shadow-[0_8px_30px_rgba(34,197,94,0.45)] transition-transform hover:scale-105 md:bottom-6 md:right-6">
      <MessageCircle size={24} />
      {unread > 0 && <span data-testid="live-chat-unread" className="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-[#FF2A5F] px-1 font-mono text-[10px] text-white">{unread}</span>}
    </Link>
  );
}
