"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Newspaper, TrendingUp, ListOrdered } from "lucide-react";
import { clsx } from "clsx";

const links = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/markets", label: "Markets", icon: TrendingUp },
  { href: "/news", label: "News", icon: Newspaper },
  { href: "/orders", label: "Place Order", icon: ListOrdered },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <nav className="border-b border-[hsl(var(--border))] bg-[hsl(var(--surface))]">
      <div className="container mx-auto px-4 max-w-7xl">
        <div className="flex items-center gap-8 h-14">
          <Link
            href="/"
            className="font-semibold text-lg text-[hsl(var(--accent))] hover:opacity-90"
          >
            Kalshi News
          </Link>
          <div className="flex gap-1">
            {links.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className={clsx(
                  "flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors",
                  pathname === href
                    ? "bg-[hsl(var(--accent))]/20 text-[hsl(var(--accent))]"
                    : "text-[hsl(var(--muted))] hover:text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-muted))]"
                )}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );
}
