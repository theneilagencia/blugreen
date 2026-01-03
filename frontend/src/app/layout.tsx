"use client";

import { Inter } from "next/font/google";
import { usePathname } from "next/navigation";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

const navLinks = [
  { href: "/", label: "Dashboard" },
  { href: "/projects", label: "Projects" },
  { href: "/create", label: "Create" },
  { href: "/assume", label: "Assume" },
  { href: "/agents", label: "Agents" },
  { href: "/quality", label: "Quality" },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  function isActive(href: string) {
    if (href === "/") {
      return pathname === "/";
    }
    return pathname.startsWith(href);
  }

  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen flex flex-col">
          <header className="bg-white border-b border-gray-200">
            <div className="max-w-7xl mx-auto px-md py-md">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-lg">
                  <a href="/" className="text-xl font-bold text-primary-600 hover:text-primary-700 transition-colors">
                    Blugreen
                  </a>
                  <nav className="flex gap-md" aria-label="Main navigation">
                    {navLinks.map((link) => (
                      <a
                        key={link.href}
                        href={link.href}
                        className={`px-sm py-xs rounded-md transition-colors ${
                          isActive(link.href)
                            ? "bg-primary-50 text-primary-700 font-medium"
                            : "text-gray-600 hover:text-primary-600 hover:bg-gray-50"
                        }`}
                        aria-current={isActive(link.href) ? "page" : undefined}
                      >
                        {link.label}
                      </a>
                    ))}
                  </nav>
                </div>
              </div>
            </div>
          </header>
          <main className="flex-1">{children}</main>
          <footer className="bg-white border-t border-gray-200 py-md">
            <div className="max-w-7xl mx-auto px-md text-center text-sm text-gray-500">
              Blugreen - Autonomous Engineering Platform
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
