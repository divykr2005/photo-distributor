import { InputHTMLAttributes, forwardRef } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className = "", label, error, id, ...props }, ref) => {
    return (
      <div className="space-y-1.5">
        {label && (
          <label
            htmlFor={id}
            className="block text-sm font-medium text-slate-300"
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={id}
          className={`
            w-full px-4 py-2.5 rounded-xl text-sm text-white
            bg-slate-800/50 border transition-all duration-200
            placeholder:text-slate-500
            focus:outline-none focus:ring-2 focus:ring-offset-0
            ${
              error
                ? "border-rose-500/50 focus:ring-rose-500/30 focus:border-rose-500"
                : "border-slate-700/50 focus:ring-violet-500/30 focus:border-violet-500"
            }
            ${className}
          `}
          {...props}
        />
        {error && (
          <p className="text-xs text-rose-400 flex items-center gap-1 mt-1">
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
