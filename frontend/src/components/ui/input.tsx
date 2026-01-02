"use client";

import { cn } from "@/lib/utils";
import { InputHTMLAttributes, forwardRef } from "react";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, error, disabled, ...props }, ref) => {
    return (
      <div className="w-full">
        <input
          ref={ref}
          className={cn(
            "w-full px-md py-sm border rounded-md text-base transition-colors",
            "focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500",
            "disabled:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50",
            error
              ? "border-danger-500 focus:ring-danger-500 focus:border-danger-500"
              : "border-gray-300",
            className
          )}
          disabled={disabled}
          {...props}
        />
        {error && (
          <p className="mt-xs text-sm text-danger-600">{error}</p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";

export { Input };
