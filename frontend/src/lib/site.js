import { useEffect, useState } from "react";
import { api } from "@/lib/api";

let cache = null;
const subs = new Set();

export async function reloadSite() {
  const { data } = await api.get("/site");
  cache = data;
  subs.forEach((f) => f(data));
  return data;
}

export function useSite() {
  const [site, setSite] = useState(cache);
  useEffect(() => {
    subs.add(setSite);
    if (!cache) reloadSite();
    return () => subs.delete(setSite);
  }, []);
  return site || { categories: [], notice: null };
}
