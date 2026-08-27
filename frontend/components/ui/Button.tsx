import { ButtonHTMLAttributes, forwardRef } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost" | "glass";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className = "",
      variant = "primary",
      size = "md",
      isLoading = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      "inline-flex items-center justify-center font-medium rounded-xl transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-zinc-950 disabled:opacity-50 disabled:pointer-events-none cursor-pointer active:scale-95";

    const variants = {
      primary:
        "bg-indigo-600 text-white hover:bg-indigo-500 focus:ring-indigo-500 shadow-[0_0_15px_-3px_rgba(99,102,241,0.4)] hover:shadow-[0_0_20px_-3px_rgba(99,102,241,0.6)] border border-indigo-500/50",
      secondary:
        "bg-zinc-800/80 text-zinc-100 border border-zinc-700/80 hover:bg-zinc-700 hover:border-zinc-600 focus:ring-zinc-500",
      glass:
        "bg-zinc-900/40 backdrop-blur-md text-zinc-200 border border-zinc-800 hover:bg-zinc-800/60 hover:border-zinc-700 focus:ring-zinc-500",
      danger:
        "bg-red-600/90 text-white hover:bg-red-500 focus:ring-red-500 shadow-lg shadow-red-600/20 border border-red-500/50",
      ghost:
        "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50 focus:ring-zinc-500",
    };

    const sizes = {
      sm: "px-3 py-1.5 text-sm",
      md: "px-5 py-2.5 text-sm",
      lg: "px-6 py-3 text-base",
    };

    return (
      <button
        ref={ref}
        className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && (
          <svg
            className="animate-spin -ml-1 mr-2 h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
        )}
        <span className={isLoading ? "opacity-90" : ""}>{children}</span>
      </button>
    );
  }
);

Button.displayName = "Button";

export default Button;
