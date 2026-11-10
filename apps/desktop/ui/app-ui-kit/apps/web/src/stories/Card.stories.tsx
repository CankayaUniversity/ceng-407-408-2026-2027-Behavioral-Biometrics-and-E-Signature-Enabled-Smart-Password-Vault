import type { Meta, StoryObj } from "@storybook/react-vite"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"

const meta = {
  title: "UI Kit/Components/Card",
  component: Card,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  decorators: [
    (Story) => (
      <div className="w-[min(92vw,440px)]">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof Card>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  render: () => (
    <Card className="border-border/70 bg-card shadow-xl shadow-black/10">
      <CardHeader>
        <CardTitle>Security overview</CardTitle>
        <CardDescription>Monitor the status of your local vault.</CardDescription>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">
        Security information appears here after the service responds.
      </CardContent>
    </Card>
  ),
}

export const TrustedSession: Story = {
  render: () => (
    <Card className="overflow-hidden border-border/70 bg-card shadow-xl shadow-black/15">
      <div className="h-1 bg-primary" />
      <CardHeader className="gap-3">
        <div className="flex items-center justify-between gap-3">
          <span className="text-xs font-semibold tracking-[0.16em] text-muted-foreground uppercase">
            Session security
          </span>
          <span className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-xs font-medium text-emerald-300">
            Trusted (demo)
          </span>
        </div>
        <CardTitle className="text-2xl tracking-tight">Identity verified</CardTitle>
        <CardDescription>
          Sample state for UI review. Real access depends on backend verification.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-3">
        <div className="rounded-lg border border-border/60 bg-background/50 p-3">
          <p className="text-xs text-muted-foreground">Device</p>
          <p className="mt-1 text-sm font-medium">Connected</p>
        </div>
        <div className="rounded-lg border border-border/60 bg-background/50 p-3">
          <p className="text-xs text-muted-foreground">Vault</p>
          <p className="mt-1 text-sm font-medium">Locked</p>
        </div>
      </CardContent>
    </Card>
  ),
}

export const VaultLocked: Story = {
  render: () => (
    <Card className="border-border/70 bg-card shadow-xl shadow-black/15">
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>Encrypted vault</CardTitle>
          <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-3 py-1 text-xs font-medium text-amber-300">
            Locked (demo)
          </span>
        </div>
        <CardDescription>
          Unlock with your master password after authentication.
        </CardDescription>
      </CardHeader>
      <CardFooter className="text-xs text-muted-foreground">
        Vault contents remain hidden while locked.
      </CardFooter>
    </Card>
  ),
}

export const Loading: Story = {
  render: () => (
    <Card aria-busy="true" className="border-border/70 bg-card">
      <CardHeader>
        <CardTitle>Checking security status</CardTitle>
        <CardDescription>Waiting for the service response...</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
        <div className="h-4 w-1/2 animate-pulse rounded bg-muted" />
        <div className="h-16 animate-pulse rounded-lg bg-muted/70" />
      </CardContent>
    </Card>
  ),
}

export const Gallery: Story = {
  parameters: { layout: "fullscreen" },
  decorators: [
    (Story) => (
      <div className="min-h-screen bg-background p-6 text-foreground md:p-10">
        <Story />
      </div>
    ),
  ],
  render: () => (
    <div className="mx-auto grid max-w-5xl gap-5 md:grid-cols-2">
      <Card className="border-border/70 bg-card">
        <CardHeader>
          <CardTitle>Security overview</CardTitle>
          <CardDescription>Shared UI kit card foundation.</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          A reusable surface for security-related information.
        </CardContent>
      </Card>
      <Card className="border-border/70 bg-card">
        <CardHeader>
          <CardTitle>Encrypted vault</CardTitle>
          <CardDescription>Vault access is currently locked.</CardDescription>
        </CardHeader>
        <CardContent>
          <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-3 py-1 text-xs text-amber-300">
            Locked (demo)
          </span>
        </CardContent>
      </Card>
    </div>
  ),
}
