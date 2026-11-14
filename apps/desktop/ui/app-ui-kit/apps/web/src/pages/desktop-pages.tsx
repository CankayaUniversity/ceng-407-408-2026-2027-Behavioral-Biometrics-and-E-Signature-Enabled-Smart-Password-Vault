import { Button } from "@workspace/ui/components/button"
import { Badge } from "@workspace/ui/components/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"

type LoginPageProps = {
  onPreview: () => void
}

export function LoginPage({ onPreview }: LoginPageProps) {
  return (
    <div className="mx-auto w-full max-w-lg py-12">
      <Card>
        <CardHeader>
          <CardTitle>
            <h2>Welcome to Aegis Vault</h2>
          </CardTitle>
          <CardDescription>
            Your behavioral authentication and password vault workspace.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <p className="text-sm leading-6 text-muted-foreground">
            Device verification and account sign-in will be connected
            in a later sprint. You can explore the interface in demo mode.
          </p>

          <Button onClick={onPreview}>
            Explore demo workspace
          </Button>

          <p className="text-xs text-muted-foreground">
            This action does not authenticate a user or unlock a vault.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

const dashboardCards = [
  {
    title: "Session",
    status: "Not authenticated",
    description: "No authentication service is connected.",
  },
  {
    title: "Password vault",
    status: "Unavailable",
    description: "Vault integration has not been connected.",
  },
  {
    title: "Fingerprint device",
    status: "Not connected",
    description: "The device simulator is not connected.",
  },
  {
    title: "Behavioral monitoring",
    status: "Not running",
    description: "No live behavioral analysis is running.",
  },
]

export function DashboardPage() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Workspace overview. These are interface placeholders,
        not live security measurements.
      </p>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {dashboardCards.map((item) => (
          <Card key={item.title}>
            <CardHeader>
              <CardTitle>
                <h2>{item.title}</h2>
              </CardTitle>
              <CardDescription>{item.description}</CardDescription>
            </CardHeader>

            <CardContent>
              <Badge variant="outline">{item.status}</Badge>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

export function SecurityStatusPage() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>
            <h2>Security overview</h2>
          </CardTitle>
          <CardDescription>
            Authentication, vault access, and behavioral risk
            will be displayed separately.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <dl className="divide-y divide-border">
            {[
              ["Authentication", "Not authenticated"],
              ["Vault access", "Unavailable"],
              ["Device verification", "Not performed"],
              ["Behavioral risk", "Unknown"],
            ].map(([label, value]) => (
              <div
                key={label}
                className="flex flex-wrap items-center justify-between gap-3 py-4"
              >
                <dt className="text-muted-foreground">{label}</dt>
                <dd>
                  <Badge variant="outline">{value}</Badge>
                </dd>
              </div>
            ))}
          </dl>

          <p className="text-xs leading-5 text-muted-foreground">
            Demo mode does not provide authentication or access
            to stored credentials.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}