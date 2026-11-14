import {
  LayoutDashboard,
  LogIn,
  ShieldCheck,
} from "lucide-react"

import { Badge } from "@workspace/ui/components/badge"
import { Navigation } from "@workspace/ui/components/navigation"

import { useAppController } from "./controllers/use-app-controller"
import {
  DashboardPage,
  LoginPage,
  SecurityStatusPage,
} from "./pages/desktop-pages"

const navigationItems = [
  {
    id: "login",
    label: "Login",
    icon: <LogIn aria-hidden="true" className="size-4" />,
  },
  {
    id: "dashboard",
    label: "Dashboard",
    icon: <LayoutDashboard aria-hidden="true" className="size-4" />,
  },
  {
    id: "security",
    label: "Security Status",
    icon: <ShieldCheck aria-hidden="true" className="size-4" />,
  },
]

export function App() {
  const { activePage, pageTitle, navigate } = useAppController()

  return (
    <div className="flex min-h-svh bg-background text-foreground">
      <aside className="flex w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar p-4">
        <div className="mb-8 flex items-center gap-3 px-2 py-3">
          <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <ShieldCheck aria-hidden="true" className="size-6" />
          </div>

          <div>
            <p className="font-semibold tracking-tight">Aegis Vault</p>
            <p className="text-xs text-muted-foreground">
              Security Workspace
            </p>
          </div>
        </div>

        <Navigation
          items={navigationItems}
          activeId={activePage}
          onNavigate={navigate}
          ariaLabel="Main navigation"
          className="w-full border-0 bg-transparent p-0"
        />

        <div className="mt-auto space-y-3 px-2 pt-8">
          <Badge variant="outline">Demo mode</Badge>
          <p className="text-xs leading-5 text-muted-foreground">
            Interface preview. No real authentication or vault access.
          </p>
        </div>
      </aside>

      <main className="min-w-0 flex-1 p-8">
        <header className="mb-8 border-b border-border pb-6">
          <p className="mb-2 text-xs uppercase tracking-widest text-muted-foreground">
            Workspace
          </p>
          <h1 className="text-3xl font-semibold tracking-tight">
            {pageTitle}
          </h1>
        </header>

        {activePage === "login" && (
          <LoginPage onPreview={() => navigate("dashboard")} />
        )}

        {activePage === "dashboard" && <DashboardPage />}

        {activePage === "security" && <SecurityStatusPage />}
      </main>
    </div>
  )
}