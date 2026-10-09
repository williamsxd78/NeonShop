import { KeyRound, LayoutTemplate, Gem, Repeat, GraduationCap, Package, Gift, Shield, Code, Gamepad2, Music, Film, Cloud, Globe, Sparkles, Zap, CreditCard, Smartphone, BookOpen, Briefcase, Image, Mail, Server, ShoppingBag } from "lucide-react";

export const ICONS = {
  key: KeyRound, layout: LayoutTemplate, gem: Gem, repeat: Repeat, graduation: GraduationCap, package: Package,
  gift: Gift, shield: Shield, code: Code, gamepad: Gamepad2, music: Music, film: Film, cloud: Cloud, globe: Globe,
  sparkles: Sparkles, zap: Zap, card: CreditCard, phone: Smartphone, book: BookOpen, briefcase: Briefcase,
  image: Image, mail: Mail, server: Server, bag: ShoppingBag,
};

export const CategoryIcon = ({ name, size = 15, ...rest }) => {
  const I = ICONS[name] || Package;
  return <I size={size} {...rest} />;
};
