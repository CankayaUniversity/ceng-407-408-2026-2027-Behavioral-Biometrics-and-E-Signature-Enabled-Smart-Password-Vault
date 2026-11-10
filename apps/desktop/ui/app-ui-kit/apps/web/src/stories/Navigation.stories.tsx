import { useState } from "react"
import type { Meta, StoryObj } from "@storybook/react-vite"
import { Button } from "@workspace/ui/components/button"
import {
  Activity,
  ChevronRight,
  Fingerprint,
  LayoutDashboard,
  LockKeyhole,
  Settings2,
  ShieldCheck,
} from "lucide-react"

type Route = "dashboard" | "vault" | "security" | "devices" | "settings"

const navigationItems = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, section: "workspace" },
  { id: "vault", label: "Password Vault", icon: LockKeyhole, section: "workspace" },
  { id: "security", label: "Security Status", icon: ShieldCheck, section: "workspace" },
  { id: "devices", label: "Devices", icon: Fingerprint, section: "workspace" },
  { id: "settings", label: "Settings", icon: Settings2, section: "preferences" },
] as const

function SidebarPreview({ initialRoute = "dashboard" }: { initialRoute?: Route }) {
  const [activeRoute, setActiveRoute] = useState<Route>(initialRoute)
  const active = navigationItems.find((item) => item.id === activeRoute)

  const renderItems = (section: "workspace" | "preferences") =>
    navigationItems
      .filter((item) => item.section === section)
      .map(({ id, label, icon: Icon }) => {
        const selected = activeRoute === id
        return (
          <button
            key={id}
            type="button"
            aria-current={selected ? "page" : undefined}
            onClick={() => setActiveRoute(id)}
            className={[
              "group flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 text-left text-sm transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              selected
                ? "border-primary/25 bg-primary/10 font-medium text-foreground shadow-sm"
                : "border-transparent text-muted-foreground hover:bg-accent hover:text-accent-foreground",
            ].join(" ")}
          >
            <Icon aria-hidden="true" className={`size-4 ${selected ? "text-primary" : ""}`} />
            <span className="flex-1">{label}</span>
            {selected && <ChevronRight aria-hidden="true" className="size-3.5 text-primary" />}
          </button>
        )
      })

  return (
    <div className="flex min-h-[520px] w-full max-w-[950px] overflow-hidden rounded-2xl border border-border bg-background text-foreground shadow-2xl">
      <aside aria-label="Demo navigation" className="flex w-[248px] shrink-0 flex-col border-r border-border bg-card/80 p-4">
        <div className="mb-8 flex items-center gap-3 px-2 pt-2">
          <div className="flex size-10 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 text-primary">
            <ShieldCheck aria-hidden="true" className="size-5" />
          </div>
          <div>
            <div className="text-sm font-semibold tracking-tight">Aegis Vault</div>
            <div className="text-xs text-muted-foreground">Security Workspace</div>
          </div>
        </div>

        <div className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-[0.13em] text-muted-foreground">
          Workspace
        </div>
        <nav aria-label="Workspace" className="space-y-1">{renderItems("workspace")}</nav>

        <div className="mt-7 mb-2 px-3 text-[11px] font-semibold uppercase tracking-[0.13em] text-muted-foreground">
          Preferences
        </div>
        <nav aria-label="Preferences" className="space-y-1">{renderItems("preferences")}</nav>

        <div className="mt-auto rounded-xl border border-border bg-background/70 p-3">
          <div className="flex items-center gap-2 text-xs font-medium">
            <span aria-hidden="true" className="size-2 rounded-full bg-emerald-400" />
            Demo mode
          </div>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            Navigation preview only. No real authentication or vault access.
          </p>
        </div>
      </aside>

      <main className="min-w-0 flex-1 p-6 md:p-8">
        <div className="mb-7 flex items-center justify-between gap-4 border-b border-border pb-5">
          <div>
            <div className="mb-1 text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground">Workspace / Preview</div>
            <h1 className="text-2xl font-semibold tracking-tight">{active?.label}</h1>
          </div>
          <Button variant="outline" size="sm" disabled>
            <Activity aria-hidden="true" className="size-4" />
            Live monitoring
          </Button>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="mb-4 flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <ShieldCheck aria-hidden="true" className="size-4" />
            </div>
            <h2 className="text-sm font-semibold">Consistent navigation</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Select a sidebar item to preview the active state. The page is intentionally mock-only.
            </p>
          </div>
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="mb-4 flex size-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
              <LockKeyhole aria-hidden="true" className="size-4" />
            </div>
            <h2 className="text-sm font-semibold">Security boundary</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Changing the selected item never grants access to protected data.
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}

const meta = {
  title: "UI Kit/Components/Navigation",
  component: SidebarPreview,
  parameters: { layout: "padded" },
  tags: ["autodocs"],
} satisfies Meta<typeof SidebarPreview>

export default meta
type Story = StoryObj<typeof meta>

export const Interactive: Story = { args: { initialRoute: "dashboard" } }
export const VaultActive: Story = { args: { initialRoute: "vault" } }
export const SecurityActive: Story = { args: { initialRoute: "security" } }
