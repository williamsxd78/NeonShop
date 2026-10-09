import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);

  const refresh = useCallback(async () => {
    if (!localStorage.getItem("nk_token")) return setUser(false);
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch {
      localStorage.removeItem("nk_token");
      setUser(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const signIn = (token, u) => { localStorage.setItem("nk_token", token); setUser(u); refresh(); };
  const signOut = () => { localStorage.removeItem("nk_token"); setUser(false); };

  return <AuthCtx.Provider value={{ user, refresh, signIn, signOut }}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);
