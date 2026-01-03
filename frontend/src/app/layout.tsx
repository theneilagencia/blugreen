import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Blugreen - Autonomous Engineering Platform",
  description: "Build, refine, and deploy SaaS products autonomously",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen flex flex-col">
          <header className="bg-white border-b border-gray-200">
            <div className="max-w-7xl mx-auto px-md py-md">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-lg">
                  <h1 className="text-xl font-bold text-primary-600">
                    Blugreen
                  </h1>
                  <nav className="flex gap-md">
                    <a
                      href="/"
                      className="text-gray-600 hover:text-primary-600 transition-colors"
                    >
                      Dashboard
                    </a>
                    <a
                      href="/projects"
                      className="text-gray-600 hover:text-primary-600 transition-colors"
                    >
                      Projects
                    </a>
                    <a
                      href="/create"
                      className="text-gray-600 hover:text-primary-600 transition-colors"
                    >
                      Create
                    </a>
                    <a
                      href="/assume"
                      className="text-gray-600 hover:text-primary-600 transition-colors"
                    >
                      Assume
                    </a>
                    <a
                      href="/agents"
                      className="text-gray-600 hover:text-primary-600 transition-colors"
                    >
                      Agents
                    </a>
                    <a
                      href="/quality"
                      className="text-gray-600 hover:text-primary-600 transition-colors"
                    >
                      Quality
                    </a>
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
