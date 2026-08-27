import { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  title?: string;
  icon?: ReactNode;
  gradient?: boolean;
}

export default function Card({
  children,
  className = "",
  title,
  icon,
  gradient = false,
}: CardProps) {
  return (
    <div
      className={`
        rounded-2xl border transition-all duration-300 relative overflow-hidden
        ${
          gradient
            ? "glass-panel bg-gradient-to-br from-zinc-900/90 to-zinc-950/90 shadow-2xl shadow-indigo-500/5"
            : "glass-card"
        }
        ${className}
      `}
    >
      {/* Subtle top highlight for depth */}
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-zinc-400/10 to-transparent"></div>
      
      {(title || icon) && (
        <div className="flex items-center gap-3 px-6 pt-6 pb-3">
          {icon && (
            <div className="p-2 rounded-xl bg-zinc-800/80 border border-zinc-700/50 text-indigo-400 shadow-inner">
              {icon}
            </div>
          )}
          {title && (
            <h3 className="text-sm font-semibold text-zinc-300 tracking-wide">
              {title}
            </h3>
          )}
        </div>
      )}
      <div className="px-6 py-5 relative z-10">{children}</div>
    </div>
  );
}
