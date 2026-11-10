import type { Meta, StoryObj } from "@storybook/react-vite"
import { Alert, AlertDescription, AlertTitle } from "@workspace/ui/components/alert"
import { AlertCircle, AlertTriangle, CheckCircle2, Info, ShieldAlert } from "lucide-react"

type AlertTone = "info" | "success" | "warning" | "error" | "reauth"

type SecurityAlertProps = {
  tone: AlertTone
  title: string
  description: string
}

const tones = {
  info: {
    Icon: Info,
    className: "border-cyan-400/25 bg-cyan-400/5",
    iconClass: "text-cyan-300",
  },
  success: {
    Icon: CheckCircle2,
    className: "border-emerald-400/25 bg-emerald-400/5",
    iconClass: "text-emerald-300",
  },
  warning: {
    Icon: AlertTriangle,
    className: "border-amber-400/25 bg-amber-400/5",
    iconClass: "text-amber-300",
  },
  error: {
    Icon: AlertCircle,
    className: "border-rose-400/25 bg-rose-400/5",
    iconClass: "text-rose-300",
  },
  reauth: {
    Icon: ShieldAlert,
    className: "border-violet-400/25 bg-violet-400/5",
    iconClass: "text-violet-300",
  },
} as const

function SecurityAlert({ tone, title, description }: SecurityAlertProps) {
  const { Icon, className, iconClass } = tones[tone]
  return (
    <Alert className={`w-full max-w-xl rounded-xl border p-5 shadow-sm ${className}`}>
      <Icon aria-hidden="true" className={`size-4 ${iconClass}`} />
      <AlertTitle className="font-semibold tracking-tight">{title}</AlertTitle>
      <AlertDescription className="leading-relaxed text-muted-foreground">
        {description}
      </AlertDescription>
    </Alert>
  )
}

const meta = {
  title: "UI Kit/Components/Alert",
  component: SecurityAlert,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  args: {
    tone: "info",
    title: "Information",
    description: "Device verification is in progress.",
  },
  argTypes: {
    tone: {
      control: "select",
      options: Object.keys(tones),
    },
  },
} satisfies Meta<typeof SecurityAlert>

export default meta
type Story = StoryObj<typeof meta>

export const Information: Story = {}
export const Success: Story = {
  args: {
    tone: "success",
    title: "Verification complete",
    description: "The authentication service confirmed the device response.",
  },
}
export const Warning: Story = {
  args: {
    tone: "warning",
    title: "Unusual activity detected",
    description: "Your session is being reviewed. Some protected actions may be unavailable.",
  },
}
export const Error: Story = {
  args: {
    tone: "error",
    title: "Device disconnected",
    description: "Verification could not finish. Reconnect the device and try again.",
  },
}
export const Reauthentication: Story = {
  args: {
    tone: "reauth",
    title: "Additional verification required",
    description: "Protected content remains locked until your session is verified again.",
  },
}
export const AllStates: Story = {
  render: () => (
    <div className="grid w-[min(560px,90vw)] gap-4">
      <SecurityAlert tone="info" title="Information" description="Device verification is in progress." />
      <SecurityAlert tone="success" title="Verification complete" description="The authentication service confirmed the device response." />
      <SecurityAlert tone="warning" title="Unusual activity detected" description="Some protected actions may be unavailable." />
      <SecurityAlert tone="error" title="Device disconnected" description="Reconnect the device and try again." />
      <SecurityAlert tone="reauth" title="Additional verification required" description="Protected content remains locked until verification succeeds." />
    </div>
  ),
}
