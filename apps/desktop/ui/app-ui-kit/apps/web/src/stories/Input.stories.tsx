import type { Meta, StoryObj } from "@storybook/react-vite"
import { Input } from "@workspace/ui/components/input"
import { Eye, Fingerprint, LockKeyhole, Mail, Search as SearchIcon, ShieldAlert } from "lucide-react"
import { useState } from "react"

const meta = {
  title: "UI Kit/Components/Input",
  component: Input,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  args: {
    placeholder: "Enter a value",
    "aria-label": "Example input",
  },
} satisfies Meta<typeof Input>

export default meta
type Story = StoryObj<typeof meta>

const field = "space-y-2"
const label = "block text-sm font-medium text-foreground"
const help = "text-xs text-muted-foreground"
const frame = "w-[min(88vw,380px)] rounded-2xl border border-border bg-card p-6 shadow-xl shadow-black/10"

export const Default: Story = {
  render: (args) => (
    <div className={frame}>
      <div className={field}>
        <label className={label} htmlFor="default-input">Account name</label>
        <Input {...args} id="default-input" placeholder="Your account name" />
        <p className={help}>This label is visible and associated with the input.</p>
      </div>
    </div>
  ),
}

export const Email: Story = {
  render: () => (
    <div className={frame}>
      <div className={field}>
        <label className={label} htmlFor="email-input">Email address</label>
        <div className="relative">
          <Mail aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input id="email-input" type="email" autoComplete="email" placeholder="name@example.com" className="pl-10" />
        </div>
      </div>
    </div>
  ),
}

function PasswordPreview() {
  const [visible, setVisible] = useState(false)
  return (
    <div className={frame}>
      <div className="mb-5 flex items-center gap-3">
        <span className="rounded-xl border border-primary/20 bg-primary/10 p-2.5 text-primary"><LockKeyhole aria-hidden="true" className="size-5" /></span>
        <div>
          <div className="font-semibold text-foreground">Unlock vault</div>
          <p className={help}>Your master password stays masked by default.</p>
        </div>
      </div>
      <div className={field}>
        <label className={label} htmlFor="master-password">Master password</label>
        <div className="relative">
          <Input id="master-password" type={visible ? "text" : "password"} autoComplete="current-password" placeholder="Enter master password" className="pr-11" />
          <button type="button" onClick={() => setVisible((current) => !current)} aria-label={visible ? "Hide password" : "Show password"} aria-pressed={visible} className="absolute right-1 top-1/2 flex size-8 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <Eye aria-hidden="true" className="size-4" />
          </button>
        </div>
        <p className={help}>Demo only. This preview does not access a real vault.</p>
      </div>
    </div>
  )
}

export const Password: Story = { render: () => <PasswordPreview /> }

export const Search: Story = {
  render: () => (
    <div className={frame}>
      <div className={field}>
        <label className={label} htmlFor="vault-search">Search vault entries</label>
        <div className="relative">
          <SearchIcon aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input id="vault-search" type="search" placeholder="Search by title..." className="pl-10" />
        </div>
      </div>
    </div>
  ),
}

export const Invalid: Story = {
  render: () => (
    <div className={frame}>
      <div className={field}>
        <label className={label} htmlFor="invalid-input">Device identifier</label>
        <Input id="invalid-input" aria-invalid="true" aria-describedby="device-error" defaultValue="invalid-id" />
        <p id="device-error" role="alert" className="flex items-center gap-2 text-xs text-destructive">
          <ShieldAlert aria-hidden="true" className="size-4 shrink-0" />
          Enter a valid device identifier.
        </p>
      </div>
    </div>
  ),
}

export const Disabled: Story = {
  render: () => (
    <div className={frame}>
      <div className={field}>
        <label className={label} htmlFor="disabled-input">Fingerprint device</label>
        <div className="relative">
          <Fingerprint aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input id="disabled-input" disabled placeholder="Unavailable" className="pl-10" />
        </div>
        <p className={help}>Input is unavailable until the device is connected.</p>
      </div>
    </div>
  ),
}

export const AllStates: Story = {
  parameters: { layout: "padded" },
  render: () => (
    <div className="grid w-[min(92vw,820px)] gap-4 md:grid-cols-2">
      <div className={frame}><label className={label} htmlFor="all-default">Default</label><Input id="all-default" placeholder="Enter a value" className="mt-2" /></div>
      <div className={frame}><label className={label} htmlFor="all-search">Search</label><Input id="all-search" type="search" placeholder="Search entries" className="mt-2" /></div>
      <div className={frame}><label className={label} htmlFor="all-invalid">Invalid</label><Input id="all-invalid" aria-invalid="true" aria-describedby="all-error" defaultValue="Invalid value" className="mt-2" /><p id="all-error" className="mt-2 text-xs text-destructive">Please check this value.</p></div>
      <div className={frame}><label className={label} htmlFor="all-disabled">Disabled</label><Input id="all-disabled" disabled placeholder="Unavailable" className="mt-2" /></div>
    </div>
  ),
}
