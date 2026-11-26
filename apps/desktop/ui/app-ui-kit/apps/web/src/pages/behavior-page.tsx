import { useEffect, useRef, useState } from "react"
import { Button } from "@workspace/ui/components/button"

type Result = {
  status: string
  model_ready?: boolean
  enrollment_sessions?: number
  verification?: { accepted: boolean; reason: string; distance: number | null; threshold: number | null } | null
  quality?: { down_down_coverage: number; flight_coverage: number } | null
}
type Action = "enroll-1" | "enroll-2" | "genuine" | "impostor"
interface BehaviorAPI {
  play(action: Action, consent: boolean): Promise<Result>
  pause(): Promise<Result>
  logout(): Promise<Result>
  deleteProfile(): Promise<Result>
}
declare global { interface Window { behavior?: BehaviorAPI } }

export function BehaviorPage() {
  const [consent, setConsent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<Result>({ status: "stopped" })
  const generation = useRef(0)
  useEffect(() => () => { generation.current++; void window.behavior?.logout() }, [])

  async function invoke(action: Action | "pause" | "logout" | "delete") {
    const current = ++generation.current
    if (!window.behavior) { setResult({ status: "desktop_bridge_unavailable" }); return }
    setBusy(true)
    setResult({ status: "working" })
    try {
      const next = action === "pause" ? await window.behavior.pause()
        : action === "logout" ? await window.behavior.logout()
        : action === "delete" ? await window.behavior.deleteProfile()
        : await window.behavior.play(action, consent)
      if (current === generation.current) setResult(next)
    } catch {
      if (current === generation.current) setResult({ status: "bridge_error" })
    } finally { if (current === generation.current) setBusy(false) }
  }

  return <section className="space-y-5 rounded-xl border border-border p-6" aria-label="Behavioral verification demonstration">
    <h2 className="text-xl font-semibold">Behavioral verification — deterministic playback</h2>
    <p>Synthetic timing demonstration. No keyboard listening or text collection. This does not sign you in or unlock a vault.</p>
    <p>Record sessions 1 and 2, then replay a separate genuine or impostor window. The threshold of 3 is for demonstration and has not been calibrated.</p>
    <label className="flex gap-2"><input type="checkbox" checked={consent} onChange={event => {
      setConsent(event.target.checked)
      if (!event.target.checked) void invoke("logout")
    }} />I consent to this local timing demonstration and storage of its synthetic profile.</label>
    <div className="flex flex-wrap gap-3">
      {([ ["enroll-1", "Record session 1"], ["enroll-2", "Record session 2"],
        ["genuine", "Replay genuine window"], ["impostor", "Replay impostor window"] ] as const).map(([action, label]) =>
        <Button key={action} disabled={!consent || busy} onClick={() => void invoke(action)}>{label}</Button>)}
      <Button variant="outline" onClick={() => void invoke("pause")}>Pause</Button>
      <Button variant="outline" onClick={() => { setConsent(false); void invoke("logout") }}>Stop / logout demo</Button>
      <Button variant="outline" onClick={() => void invoke("delete")}>Delete demo profile</Button>
    </div>
    <div role="status" aria-live="polite">
      <p>Status: {result.status}</p>
      {result.model_ready !== undefined && <p>Model: {result.model_ready ? "ready" : "not ready"}</p>}
      {result.enrollment_sessions !== undefined && <p>Pending enrollment sessions: {result.enrollment_sessions}</p>}
      {result.verification && <p>Behavioral observation: {result.verification.reason}; distance {result.verification.distance?.toFixed(3)} (threshold {result.verification.threshold}). No access decision.</p>}
      {result.quality && <p>Transition coverage: {(result.quality.down_down_coverage * 100).toFixed(0)}% / {(result.quality.flight_coverage * 100).toFixed(0)}%</p>}
    </div>
    <p className="text-sm text-muted-foreground">Pausing or leaving this page stops the worker and clears pending enrollment and input. Saved synthetic profiles remain until deleted. Live account integration awaits APP-03.</p>
  </section>
}
