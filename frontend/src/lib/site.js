import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { applyTheme, applyFonts } from "@/lib/theme";

let cache = null;
const subs = new Set();

export const DEFAULT_BRAND = { name_start: "Card", name_end: "Wizard", icon: "sparkles", page_title: "CardWizard – Gift Cards & Digital Goods", official_store: "CardWizard Official" };
const EMPTY = { categories: [], category_style: {}, notice: null, hero: null, banners: [], product_count: 0,
  brand: DEFAULT_BRAND, footer: { text: "", columns: [] }, sections: null, theme: null };

export async function reloadSite() {
  const { data } = await api.get("/site");
  cache = data;
  applyTheme(data.theme);
  applyFonts(data.fonts);
  if (data.brand?.page_title) document.title = data.brand.page_title;
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
  return site || EMPTY;
}
