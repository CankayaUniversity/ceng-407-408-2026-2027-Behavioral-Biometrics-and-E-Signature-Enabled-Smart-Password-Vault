import type { Meta, StoryObj } from "@storybook/react-vite"
import { Badge } from "@workspace/ui/components/badge"
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  HelpCircle,
  LockKeyhole,
  ShieldAlert,
} from "lucide-react"

type SecurityStatus =
  | "trusted"
  | "suspicious"
  | "reauth_required"
  | "locked"
  | "expired"
  | "unknown"

type SecurityBadgeProps = { status: SecurityStatus }

const statuses = {
  trusted: {
    label: "Trusted",
    Icon: CheckCircle2,
    className: "border-emerald-400/25 bg-emerald-400/10 text-emerald-300",
  },
  suspicious: {
    label: "Suspicious",
    Icon: AlertTriangle,
    className: "border-amber-400/25 bg-amber-400/10 text-amber-300",
  },
  reauth_required: {
    label: "Re-auth required",
    Icon: ShieldAlert,
    className: "border-violet-400/25 bg-violet-400/10 text-violet-300",
  },
  locked: {
    label: "Locked",
    Icon: LockKeyhole,
    className: "border-rose-400/25 bg-rose-400/10 text-rose-300",
  },
  expired: {
    label: "Expired",
    Icon: Clock3,
    className: "border-slate-400/25 bg-slate-400/10 text-slate-300",
  },
  unknown: {
    label: "Unknown",
    Icon: HelpCircle,
    className: "border-slate-400/25 bg-slate-400/10 text-slate-300",
  },
} as const

function SecurityStatusBadge({ status }: SecurityBadgeProps) {
  const { label, Icon, className } = statuses[status]
  return (
    <Badge
      variant="outline"
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${className}`}
    >
      <Icon aria-hidden="true" className="size-3.5" />
      {label}
    </Badge>
  )
}

const meta = {
  title: "UI Kit/Security/StatusBadge",
  component: SecurityStatusBadge,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  args: { status: "trusted" },
  argTypes: {
    status: {
      control: "select",
      options: Object.keys(statuses),
    },
  },
} satisfies Meta<typeof SecurityStatusBadge>

export default meta
type Story = StoryObj<typeof meta>

export const Interactive: Story = {}
export const Trusted: Story = { args: { status: "trusted" } }
export const Suspicious: Story = { args: { status: "suspicious" } }
export const ReauthRequired: Story = { args: { status: "reauth_required" } }
export const Locked: Story = { args: { status: "locked" } }
export const Expired: Story = { args: { status: "expired" } }
export const Unknown: Story = { args: { status: "unknown" } }

export const AllStates: Story = {
  render: () => (
    <div className="grid min-w-80 gap-4 rounded-2xl border border-border bg-card p-6 shadow-xl shadow-black/10">
      <div>
        <h3 className="text-sm font-semibold text-foreground">Security states</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          Preview only — these labels do not authorize access.
        </p>
      </div>
      <div className="flex flex-wrap gap-3">
        {(Object.keys(statuses) as SecurityStatus[]).map((status) => (
          <SecurityStatusBadge key={status} status={status} />
        ))}
      </div>
    </div>
  ),
}
