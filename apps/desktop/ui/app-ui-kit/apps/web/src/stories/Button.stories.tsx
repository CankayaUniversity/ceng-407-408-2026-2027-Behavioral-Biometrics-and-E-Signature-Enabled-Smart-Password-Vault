import type { Meta, StoryObj } from "@storybook/react-vite"
import { ArrowRight, Fingerprint, KeyRound, LoaderCircle, LockKeyhole, ShieldCheck } from "lucide-react"
import { Button } from "@workspace/ui/components/button"

const meta = {
  title: "UI Kit/Components/Button",
  component: Button,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  args: { children: "Continue", variant: "default", size: "default" },
  argTypes: {
    variant: {
      control: "select",
      options: ["default", "secondary", "outline", "ghost", "destructive", "link"],
    },
    size: {
      control: "select",
      options: ["default", "xs", "sm", "lg", "icon", "icon-xs", "icon-sm", "icon-lg"],
    },
    disabled: { control: "boolean" },
  },
} satisfies Meta<typeof Button>

export default meta
type Story = StoryObj<typeof meta>

export const Primary: Story = {
  args: { children: "Continue", variant: "default" },
}

export const Secondary: Story = {
  args: { children: "Cancel", variant: "secondary" },
}

export const Outline: Story = {
  args: { children: "View details", variant: "outline" },
}

export const Destructive: Story = {
  args: { children: "Lock vault", variant: "destructive" },
}

export const Disabled: Story = {
  args: { children: "Unavailable", disabled: true },
}

// The current shared Button has no `loading` prop. Use an accessible,
// disabled loading composition until loading is implemented in the component.
export const LoadingExample: Story = {
  render: () => (
    <Button disabled aria-busy="true">
      <LoaderCircle className="animate-spin" aria-hidden="true" />
      Verifying device...
    </Button>
  ),
}

export const AllVariants: Story = {
  render: () => (
    <div className="flex max-w-2xl flex-wrap items-center gap-3 rounded-2xl border border-border bg-card p-6 shadow-sm">
      <Button variant="default">Primary</Button>
      <Button variant="secondary">Secondary</Button>
      <Button variant="outline">Outline</Button>
      <Button variant="ghost">Ghost</Button>
      <Button variant="destructive">Destructive</Button>
      <Button variant="link">Link</Button>
    </div>
  ),
}

export const AllSizes: Story = {
  render: () => (
    <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-border bg-card p-6">
      <Button size="xs">Extra small</Button>
      <Button size="sm">Small</Button>
      <Button size="default">Default</Button>
      <Button size="lg">Large</Button>
      <Button size="icon" aria-label="Security verified"><ShieldCheck aria-hidden="true" /></Button>
      <Button size="icon-sm" aria-label="Fingerprint"><Fingerprint aria-hidden="true" /></Button>
    </div>
  ),
}

export const SecurityActions: Story = {
  parameters: { layout: "padded" },
  render: () => (
    <div className="w-full max-w-2xl space-y-5 rounded-2xl border border-border bg-card p-6 shadow-xl">
      <div className="flex items-start gap-3">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 text-primary">
          <ShieldCheck aria-hidden="true" className="size-5" />
        </div>
        <div className="space-y-1">
          <h3 className="font-semibold tracking-tight text-card-foreground">Secure workspace</h3>
          <p className="text-sm text-muted-foreground">
            Sample UI actions. These buttons do not grant access or change session state.
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-3">
        <Button><Fingerprint aria-hidden="true" />Verify identity<ArrowRight aria-hidden="true" /></Button>
        <Button variant="secondary"><KeyRound aria-hidden="true" />Unlock vault</Button>
        <Button variant="outline"><ShieldCheck aria-hidden="true" />Security status</Button>
        <Button variant="destructive"><LockKeyhole aria-hidden="true" />Lock vault</Button>
      </div>
    </div>
  ),
}
