import { InputHTMLAttributes, forwardRef } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className = "", label, error, id, ...props }, ref) => {
    return (
      <div className="space-y-1.5 group">
        {label && (
          <label
            htmlFor={id}
            className="block text-sm font-medium text-zinc-300 group-focus-within:text-indigo-400 transition-colors duration-200"
          >
            {label}
          </label>
        )}
        <div className="relative">
          <input
            ref={ref}
            id={id}
            className={`
              w-full px-4 py-2.5 rounded-xl text-sm text-white
              bg-zinc-900/60 border backdrop-blur-sm transition-all duration-300
              placeholder:text-zinc-600
              focus:outline-none focus:ring-4 focus:ring-offset-0 focus:bg-zinc-900
              ${
                error
                  ? "border-red-500/50 focus:ring-red-500/20 focus:border-red-500"
                  : "border-zinc-800/80 focus:ring-indigo-500/20 focus:border-indigo-500 hover:border-zinc-700"
              }
              ${className}
            `}
            {...props}
          />
        </div>
        {error && (
          <p className="text-xs text-red-400 flex items-center gap-1 mt-1 animate-in">
            <svg
              className="w-3.5 h-3.5 flex-shrink-0"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            {error}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";

export default Input;
