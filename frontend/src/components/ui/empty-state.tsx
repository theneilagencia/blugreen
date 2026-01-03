"use client";

import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";
import { ReactNode } from "react";
import { Button } from "./button";

export interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
    icon?: LucideIcon;
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  children?: ReactNode;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  secondaryAction,
  children,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-lg px-md text-center",
        className
      )}
    >
      {Icon && (
        <div className="mb-md">
          <div className="p-md bg-gray-100 rounded-full inline-flex">
            <Icon className="h-8 w-8 text-gray-400" />
          </div>
        </div>
      )}

      <h3 className="text-lg font-semibold text-gray-900 mb-xs">{title}</h3>

      {description && (
        <p className="text-gray-500 max-w-md mb-md">{description}</p>
      )}

      {children}

      {(action || secondaryAction) && (
        <div className="flex gap-sm mt-md">
          {secondaryAction && (
            <Button variant="secondary" onClick={secondaryAction.onClick}>
              {secondaryAction.label}
            </Button>
          )}
          {action && (
            <Button onClick={action.onClick}>
              {action.icon && <action.icon className="h-4 w-4 mr-2" />}
              {action.label}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

export function TableEmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: Omit<EmptyStateProps, "children" | "secondaryAction">) {
  return (
    <EmptyState
      icon={Icon}
      title={title}
      description={description}
      action={action}
      className={cn("py-xl", className)}
    />
  );
}
