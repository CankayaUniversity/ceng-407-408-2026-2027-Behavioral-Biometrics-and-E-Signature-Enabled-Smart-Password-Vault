import { useEffect, useRef, useState, useSyncExternalStore } from "react"
import { Button } from "@workspace/ui/components/button"
import { Input } from "@workspace/ui/components/input"
import { Badge } from "@workspace/ui/components/badge"
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@workspace/ui/components/card"
import { EnrollmentController } from "../enrollment/controller"
import {
  createMockService,
  desktopService,
  MOCK_SCENARIOS,
} from "../enrollment/service"
import type { MockScenario } from "../enrollment/service"

const fingers = ["thumb", "index", "middle", "ring", "little"]
const slots = ["left", "right"].flatMap((hand) =>
  fingers.map((finger) => `${hand}_${finger}`)
)
const label = (slot: string) => slot.replace("_", " ")
const messages: Record<string, string> = {
  VALIDATION_ERROR: "Check the display name, device ID and finger selection.",
  DEVICE_ALREADY_REGISTERED:
    "This device ID is already registered. Its owner has not been changed. Review the existing registration before starting another attempt.",
  PAIRING_EXPIRED:
    "The pairing code is expired, invalid or already used. This API cannot renew it. Review the pending account before restarting.",
  DEVICE_REJECTED:
    "The simulator rejected finger enrollment. You can retry this step.",
  DISCONNECTED:
    "Could not connect to the local backend. Start the backend, then retry if available or start a new attempt.",
  OUTCOME_UNKNOWN:
    "The result could not be confirmed. A server record may already exist. Automatic retry is disabled to avoid duplicate records; review the backend before starting again.",
  BRIDGE_UNAVAILABLE:
    "The Python bridge stopped or could not start. Check Python dependencies and AEGIS_PYTHON. A server request may already have completed.",
  ALREADY_STARTED:
    "An enrollment attempt already exists. Cancel it before starting another.",
}

export function EnrollmentPage() {
  const available = Boolean(window.enrollment)
  const [mode, setMode] = useState<"mock" | "local">(
    available ? "local" : "mock"
  )
  const [scenario, setScenario] = useState<MockScenario>("success")
  const [controller, setController] = useState(
    () =>
      new EnrollmentController(
        available ? desktopService() : createMockService()
      )
  )
  const state = useSyncExternalStore(
    controller.subscribe,
    controller.getSnapshot
  )
  const [step, setStep] = useState(0)
  const [displayName, setDisplayName] = useState("")
  const [deviceId, setDeviceId] = useState("")
  const [fingerSlot, setFingerSlot] = useState("right_index")
  const [confirmCancel, setConfirmCancel] = useState(false)
  const heading = useRef<HTMLHeadingElement>(null)
  const dialog = useRef<HTMLDialogElement>(null)
  const started = state.status !== "idle"
  const busy = state.status === "running"
  const snapshot = state.snapshot
  const input = { displayName, deviceId, fingerSlot }

  useEffect(() => {
    heading.current?.focus()
  }, [step, state.status])
  useEffect(() => {
    if (confirmCancel) dialog.current?.showModal()
    else dialog.current?.close()
  }, [confirmCancel])

  async function restart() {
    await controller.cancel()
    setController(
      new EnrollmentController(
        mode === "local" ? desktopService() : createMockService(scenario)
      )
    )
    setStep(0)
    setDisplayName("")
    setDeviceId("")
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="space-y-2">
        <Badge variant="outline">
          {mode === "mock"
            ? "Mock demo · no server writes"
            : "Local backend · simulated device"}
        </Badge>
        <p className="text-sm text-muted-foreground">
          Only simulated finger slots are used. No real fingerprint is captured.
          Enrollment does not sign you in or unlock a vault.
        </p>
        <p className="text-sm text-muted-foreground">
          The simulator keeps keys and finger slots in memory for this attempt.
          Cancelling, restarting or closing the app discards them; server
          records remain. Persistent device storage is not implemented.
        </p>
      </div>

      {!started && step === 0 && (
        <div className="flex flex-wrap gap-4">
          <label className="grid gap-2 text-sm">
            Service
            <select
              className="rounded-md border bg-background p-2"
              value={mode}
              onChange={(event) => {
                const next = event.target.value as "mock" | "local"
                setMode(next)
                setController(
                  new EnrollmentController(
                    next === "local"
                      ? desktopService()
                      : createMockService(scenario)
                  )
                )
              }}
            >
              <option value="mock">Independent mock demo</option>
              <option value="local" disabled={!available}>
                Local backend + Python simulator
                {!available ? " (Electron required)" : ""}
              </option>
            </select>
          </label>
          {mode === "mock" && (
            <label className="grid gap-2 text-sm">
              Demo scenario
              <select
                className="rounded-md border bg-background p-2"
                value={scenario}
                onChange={(event) => {
                  const next = event.target.value as MockScenario
                  setScenario(next)
                  setController(
                    new EnrollmentController(createMockService(next))
                  )
                }}
              >
                {MOCK_SCENARIOS.map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </label>
          )}
        </div>
      )}

      <ol
        aria-label="Enrollment steps"
        className="flex flex-wrap gap-4 text-sm"
      >
        {["User", "Device & finger", "Review", "Result"].map((title, index) => (
          <li
            key={title}
            aria-current={step === index ? "step" : undefined}
            className={
              step === index
                ? "font-semibold text-primary"
                : "text-muted-foreground"
            }
          >
            {index + 1}. {title}
          </li>
        ))}
      </ol>

      <Card>
        <CardHeader>
          <CardTitle>
            <h2 ref={heading} tabIndex={-1} className="outline-none">
              {step === 0
                ? "Create your user"
                : step === 1
                  ? "Choose a simulated device"
                  : step === 2
                    ? "Review enrollment"
                    : "Enrollment result"}
            </h2>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {step < 2 && (
            <form
              className="space-y-5"
              onSubmit={(event) => {
                event.preventDefault()
                setStep(step + 1)
              }}
            >
              {step === 0 ? (
                <div className="space-y-2">
                  <label htmlFor="display-name">Display name</label>
                  <Input
                    id="display-name"
                    value={displayName}
                    onChange={(event) => setDisplayName(event.target.value)}
                    required
                    maxLength={100}
                    pattern=".*\S.*"
                    aria-describedby="name-help"
                  />
                  <p id="name-help" className="text-sm text-muted-foreground">
                    Required, 1–100 characters. This is not a unique login name.
                    No password is needed for this registration API.
                  </p>
                </div>
              ) : (
                <>
                  <div className="space-y-2">
                    <label htmlFor="device-id">Simulated device ID</label>
                    <Input
                      id="device-id"
                      value={deviceId}
                      onChange={(event) => setDeviceId(event.target.value)}
                      required
                      maxLength={36}
                      pattern=".*\S.*"
                      aria-describedby="device-help"
                    />
                    <p
                      id="device-help"
                      className="text-sm text-muted-foreground"
                    >
                      Choose an unused ID, up to 36 characters.
                    </p>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setDeviceId(crypto.randomUUID())}
                    >
                      Generate device ID
                    </Button>
                  </div>
                  <div className="grid gap-2">
                    <label htmlFor="finger-slot">Finger slot</label>
                    <select
                      id="finger-slot"
                      className="rounded-md border bg-background p-2 capitalize"
                      value={fingerSlot}
                      onChange={(event) => setFingerSlot(event.target.value)}
                    >
                      {slots.map((slot) => (
                        <option value={slot} key={slot}>
                          {label(slot)}
                        </option>
                      ))}
                    </select>
                  </div>
                </>
              )}
              <div className="flex gap-3">
                {step === 1 && (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setStep(0)}
                  >
                    Back
                  </Button>
                )}
                <Button type="submit">Continue</Button>
              </div>
            </form>
          )}

          {step === 2 && !started && (
            <div className="space-y-5">
              <dl className="space-y-2">
                <div>
                  <dt>Display name</dt>
                  <dd>{displayName.trim()}</dd>
                </div>
                <div>
                  <dt>Device ID</dt>
                  <dd className="break-all">{deviceId.trim()}</dd>
                </div>
                <div>
                  <dt>Simulated finger</dt>
                  <dd className="capitalize">{label(fingerSlot)}</dd>
                </div>
              </dl>
              <p className="text-sm text-muted-foreground">
                {mode === "local"
                  ? "This creates a backend user, enrolls a simulated finger and pairs the device. Pairing must complete within five minutes. Cancellation does not remove backend records."
                  : "This demonstration uses fixed mock responses. It does not register a real account or device."}
              </p>
              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep(1)}>
                  Back
                </Button>
                <Button
                  onClick={() => {
                    setStep(3)
                    void controller.run(input)
                  }}
                >
                  Start enrollment
                </Button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <div role="status" aria-live="polite">
                {busy
                  ? state.phase === "registration"
                    ? "Creating user…"
                    : "Enrolling simulated finger and pairing device…"
                  : state.status === "success"
                    ? "Enrollment steps completed. Backend status: PENDING."
                    : state.status === "cancelled"
                      ? "Enrollment cancelled."
                      : "Enrollment needs attention."}
              </div>
              {state.error && (
                <p
                  role="alert"
                  className="rounded-md border border-destructive p-3 text-sm"
                >
                  {messages[state.error] ??
                    "Enrollment could not be completed. Review the current result before restarting."}
                </p>
              )}
              {state.status === "cancelled" && (
                <p className="text-sm">
                  Requests already sent may have completed. Server records were
                  not deleted. Local simulator keys have been discarded.
                </p>
              )}
              <dl className="space-y-2 text-sm">
                <div>
                  <dt>User registration</dt>
                  <dd>
                    {snapshot?.registered
                      ? `Created · ${snapshot.userId}`
                      : "Not confirmed"}
                  </dd>
                </div>
                <div>
                  <dt>Device ID</dt>
                  <dd className="break-all">
                    {snapshot?.deviceId ?? deviceId}
                  </dd>
                </div>
                <div>
                  <dt>Finger slot</dt>
                  <dd className="capitalize">
                    {label(snapshot?.fingerSlot ?? fingerSlot)} ·{" "}
                    {snapshot?.enrolled
                      ? "Enrolled in simulator"
                      : "Not confirmed"}
                  </dd>
                </div>
                <div>
                  <dt>Backend device pairing</dt>
                  <dd>
                    {snapshot?.paired
                      ? snapshot.pairingStatus
                      : "Not confirmed"}
                  </dd>
                </div>
              </dl>
              {state.status === "success" && (
                <p className="text-sm text-muted-foreground">
                  {mode === "mock" ? "Mock result only. " : ""}No authenticated
                  session was created. Vault access remains locked.
                </p>
              )}
              {state.status === "error" && state.retryable && (
                <Button onClick={() => void controller.run(input)}>
                  Retry failed step
                </Button>
              )}
              {!busy && (
                <Button variant="outline" onClick={() => void restart()}>
                  Start a new enrollment
                </Button>
              )}
            </div>
          )}
          {state.status !== "cancelled" && state.status !== "success" && (
            <Button
              className="mt-5"
              variant="outline"
              onClick={() => setConfirmCancel(true)}
            >
              Cancel enrollment
            </Button>
          )}
        </CardContent>
      </Card>

      <dialog
        ref={dialog}
        aria-labelledby="cancel-title"
        onCancel={() => setConfirmCancel(false)}
        className="m-auto max-w-md rounded-xl border bg-background p-6 text-foreground backdrop:bg-black/60"
      >
        <h2 id="cancel-title" className="mb-3 text-lg font-semibold">
          Cancel enrollment?
        </h2>
        <p className="mb-5 text-sm">
          Server records will remain, and requests already sent may complete.
          The local simulated device will be discarded.
        </p>
        <div className="flex gap-3">
          <Button autoFocus onClick={() => setConfirmCancel(false)}>
            Keep enrolling
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              setConfirmCancel(false)
              setStep(3)
              void controller.cancel()
            }}
          >
            Confirm cancellation
          </Button>
        </div>
      </dialog>
    </div>
  )
}
