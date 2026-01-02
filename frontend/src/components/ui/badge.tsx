"use client";

import { cn } from "@/lib/utils";
import { ReactNode } from "react";

export interface BadgeProps {
  variant?: "default" | "primary" | "success" | "warning" | "danger";
  children: ReactNode;
  className?: string;
}

export function Badge({ variant = "default", children, className }: BadgeProps) {
  const variants = {
    default: "bg-gray-100 text-gray-800",
    primary: "bg-primary-100 text-primary-800",
    success: "bg-green-100 text-green-800",
    warning: "bg-yellow-100 text-yellow-800",
    danger: "bg-danger-100 text-danger-800",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-sm",
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
