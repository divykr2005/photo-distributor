"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  HiOutlineViewGrid,
  HiOutlineCalendar,
  HiOutlineUserGroup,
  HiOutlineCog,
} from "react-icons/hi";

const navItems = [
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: HiOutlineViewGrid,
  },
  {
    label: "Events",
    href: "/events",
    icon: HiOutlineCalendar,
  },
  {
    label: "Guests",
    href: "/guests",
    icon: HiOutlineUserGroup,
  },
  {
    label: "Settings",
    href: "/settings",
    icon: HiOutlineCog,
  },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r border-slate-700/50 bg-slate-900/40 backdrop-blur-sm hidden lg:flex flex-col">
      <nav className="flex-1 px-4 py-6 space-y-1.5">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href || pathname?.startsWith(item.href + "/");
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`
                flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium
                transition-all duration-200 group
                ${
                  isActive
                    ? "bg-violet-600/15 text-violet-300 border border-violet-500/20 shadow-sm shadow-violet-500/5"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent"
                }
              `}
            >
              <Icon
                className={`w-5 h-5 transition-colors ${
                  isActive
                    ? "text-violet-400"
                    : "text-slate-500 group-hover:text-slate-300"
                }`}
              />
              {item.label}
              {isActive && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-violet-400 shadow-sm shadow-violet-400" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Bottom section */}
      <div className="px-4 py-4 border-t border-slate-700/30">
        <div className="px-4 py-3 rounded-xl bg-gradient-to-br from-violet-600/10 to-indigo-600/10 border border-violet-500/10">
          <p className="text-xs font-medium text-violet-300">Week 1 Build</p>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Registration &amp; Infrastructure
          </p>
        </div>
      </div>
    </aside>
  );
}
