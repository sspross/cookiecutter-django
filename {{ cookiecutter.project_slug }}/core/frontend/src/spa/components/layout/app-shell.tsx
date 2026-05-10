import { useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router";
import { readCsrfCookie } from "@/api/csrf";
import { HomeIcon, KeyIcon, Menu, X } from "@/components/layout/icons";
import { Logo } from "@/components/layout/logo";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { cn } from "@/lib/utils";

interface AppShellProps {
  projectName: string;
  username?: string;
  children: React.ReactNode;
}

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", Icon: HomeIcon, end: true },
  { to: "/api-access", label: "API Access", Icon: KeyIcon, end: false },
];

function LogoutForm({ className }: { className?: string }) {
  // Django's LogoutView only accepts POST; render a form submit styled as
  // a link rather than an <a href>, which would 405.
  const csrfToken = readCsrfCookie() ?? "";
  return (
    <form method="post" action="/accounts/logout/" className={className}>
      <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
      <button type="submit" className="hover:underline">
        Log out
      </button>
    </form>
  );
}

export function AppShell({ projectName, username, children }: AppShellProps) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const { pathname } = useLocation();
  // biome-ignore lint/correctness/useExhaustiveDependencies: pathname is the trigger to close nav on route change
  useEffect(() => setMobileNavOpen(false), [pathname]);
  return (
    <div className="flex h-screen w-full overflow-hidden bg-background text-foreground">
      <aside
        className="hidden w-60 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground md:flex"
        data-testid="sidebar"
      >
        <div className="flex items-center justify-center border-b border-sidebar-border px-4 py-3">
          <Link to="/" aria-label={projectName} className="hover:opacity-80">
            <Logo label={projectName} />
          </Link>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {NAV_ITEMS.map(({ to, label, Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium",
                  "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                  isActive && "bg-sidebar-accent text-sidebar-accent-foreground",
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-sidebar-border p-3 text-xs text-muted-foreground">
          {username ? `Signed in as ${username}` : null}
          <div className="mt-2 flex items-center justify-between">
            <ThemeToggle />
            <LogoutForm />
          </div>
        </div>
      </aside>
      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-col border-b border-border md:hidden">
          <div className="flex items-center gap-4 px-4 py-3">
            <Link to="/" aria-label={projectName} className="hover:opacity-80">
              <Logo label={projectName} />
            </Link>
            <div className="ml-auto flex items-center gap-2">
              <button
                type="button"
                onClick={() => setMobileNavOpen((v) => !v)}
                aria-expanded={mobileNavOpen}
                aria-controls="mobile-nav"
                aria-label={mobileNavOpen ? "Close menu" : "Open menu"}
                className="inline-flex h-9 w-9 items-center justify-center rounded-md hover:bg-accent hover:text-accent-foreground"
              >
                {mobileNavOpen ? (
                  <X className="h-5 w-5" />
                ) : (
                  <Menu className="h-5 w-5" />
                )}
              </button>
            </div>
          </div>
          {mobileNavOpen ? (
            <nav
              id="mobile-nav"
              className="flex flex-col gap-1 border-t border-border bg-sidebar px-3 py-3 text-sidebar-foreground"
            >
              {NAV_ITEMS.map(({ to, label, Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium",
                      "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                      isActive && "bg-sidebar-accent text-sidebar-accent-foreground",
                    )
                  }
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </NavLink>
              ))}
              <div className="mt-2 border-t border-sidebar-border pt-3 text-xs text-muted-foreground">
                {username ? <div>Signed in as {username}</div> : null}
                <div className="mt-2 flex items-center justify-between">
                  <ThemeToggle />
                  <LogoutForm />
                </div>
              </div>
            </nav>
          ) : null}
        </header>
        <div className="min-w-0 flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-8">
          {children}
        </div>
      </main>
    </div>
  );
}
