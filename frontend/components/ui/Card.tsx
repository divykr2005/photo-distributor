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
        rounded-2xl border transition-all duration-300
        ${
          gradient
            ? "bg-gradient-to-br from-slate-800/80 to-slate-900/80 border-slate-700/50 shadow-xl shadow-black/20"
            : "bg-slate-800/40 border-slate-700/30 hover:border-slate-600/50"
        }
        backdrop-blur-sm
        ${className}
      `}
    >
      {(title || icon) && (
        <div className="flex items-center gap-3 px-6 pt-5 pb-2">
          {icon && (
            <div className="p-2 rounded-lg bg-slate-700/50 text-violet-400">
              {icon}
            </div>
          )}
          {title && (
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
              {title}
            </h3>
          )}
        </div>
      )}
      <div className="px-6 py-4">{children}</div>
    </div>
  );
}
