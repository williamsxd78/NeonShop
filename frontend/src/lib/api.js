import axios from "axios";

const BACKEND = process.env.REACT_APP_BACKEND_URL;
export const api = axios.create({ baseURL: `${BACKEND}/api` });

api.interceptors.request.use((c) => {
  const t = localStorage.getItem("nk_token");
  if (t) c.headers.Authorization = `Bearer ${t}`;
  return c;
});

export function errMsg(e) {
  const d = e?.response?.data?.detail;
  if (d == null) return e?.message || "Something went wrong";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x?.msg || JSON.stringify(x)).join(" ");
  return d.msg || String(d);
}

export const money = (c) => `$${((c || 0) / 100).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
export const imgSrc = (u) => (u && u.startsWith("/api/") ? `${BACKEND}${u}` : u);
export const fmtDate = (s) => (s ? new Date(s).toLocaleString() : "-");
export const COIN_LABEL = { BTC: "BTC", USDT_TRC20: "USDT · TRC20", USDT_BEP20: "USDT · BEP20", LTC: "LTC", ETH: "ETH" };
