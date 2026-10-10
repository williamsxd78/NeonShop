import { useSite, DEFAULT_BRAND } from "@/lib/site";
import { CategoryIcon } from "@/components/CategoryIcon";

export const useBrand = () => useSite().brand || DEFAULT_BRAND;

export function BrandName({ className = "" }) {
  const b = useBrand();
  return <span className={`font-display tracking-tight ${className}`} data-testid="brand-name">{b.name_start}<span className="text-brand">{b.name_end}</span></span>;
}

export function BrandMark({ size = 18, className = "h-9 w-9" }) {
  const b = useBrand();
  return (
    <span className={`grid place-items-center rounded-lg bg-brand/10 text-brand shadow-[0_0_18px_rgb(var(--nk-brand)/0.35)] ${className}`}>
      <CategoryIcon name={b.icon} size={size} />
    </span>
  );
}
