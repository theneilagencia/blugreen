"use client";

import { cn } from "@/lib/utils";
import { ChevronRight, Home } from "lucide-react";
import { Fragment } from "react";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export interface BreadcrumbProps {
  items: BreadcrumbItem[];
  className?: string;
  showHome?: boolean;
}

export function Breadcrumb({
  items,
  className,
  showHome = true,
}: BreadcrumbProps) {
  const allItems: BreadcrumbItem[] = showHome
    ? [{ label: "Home", href: "/" }, ...items]
    : items;

  return (
    <nav
      aria-label="Breadcrumb"
      className={cn("flex items-center text-sm", className)}
    >
      <ol className="flex items-center gap-xs">
        {allItems.map((item, index) => {
          const isLast = index === allItems.length - 1;
          const isHome = index === 0 && showHome;

          return (
            <Fragment key={index}>
              <li className="flex items-center">
                {item.href && !isLast ? (
                  <a
                    href={item.href}
                    className="flex items-center gap-xs text-gray-500 hover:text-primary-600 transition-colors"
                  >
                    {isHome && <Home className="h-4 w-4" />}
                    {!isHome && <span>{item.label}</span>}
                  </a>
                ) : (
                  <span
                    className={cn(
                      "flex items-center gap-xs",
                      isLast
                        ? "text-gray-900 font-medium"
                        : "text-gray-500"
                    )}
                    aria-current={isLast ? "page" : undefined}
                  >
                    {isHome && <Home className="h-4 w-4" />}
                    {!isHome && item.label}
                  </span>
                )}
              </li>
              {!isLast && (
                <li aria-hidden="true">
                  <ChevronRight className="h-4 w-4 text-gray-400" />
                </li>
              )}
            </Fragment>
          );
        })}
      </ol>
    </nav>
  );
}

export function PageHeader({
  title,
  description,
  breadcrumbs,
  actions,
  className,
}: {
  title: string;
  description?: string;
  breadcrumbs?: BreadcrumbItem[];
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mb-lg", className)}>
      {breadcrumbs && breadcrumbs.length > 0 && (
        <Breadcrumb items={breadcrumbs} className="mb-sm" />
      )}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
          {description && (
            <p className="text-gray-600 mt-xs">{description}</p>
          )}
        </div>
        {actions && <div className="flex gap-sm">{actions}</div>}
      </div>
    </div>
  );
}
