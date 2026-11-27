import { test } from "node:test"
import assert from "node:assert/strict"
import { mkdtempSync, readdirSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import path from "node:path"
import { BehaviorBridge } from "../electron/behavior.cjs"
const directory = () => mkdtempSync(path.join(tmpdir(), "aegis-ai05-"))

test("real Python bridge: consent, enrollment, scores, deletion and restart", async () => {
  const root = directory()
  const bridge = new BehaviorBridge(root)
  try {
    assert.equal((await bridge.call("play", { action: "genuine", consent: false })).status, "consent_required")
    assert.equal((await bridge.call("play", { action: "genuine", consent: true })).status, "model_not_ready")
    assert.equal((await bridge.call("play", { action: "enroll-1", consent: true })).enrollment_sessions, 1)
    assert.equal((await bridge.call("play", { action: "enroll-2", consent: true })).status, "ready")
    const genuine = await bridge.call("play", { action: "genuine", consent: true })
    assert.equal(genuine.verification.reason, "match")
    assert.equal(genuine.source, "synthetic-playback")
    assert.equal(genuine.feature_version, "timing-summary-v2")
    assert.equal((await bridge.call("play", { action: "impostor", consent: true })).verification.accepted, false)
    await bridge.call("logout")
    assert.equal(bridge.child, null)
    assert.equal((await bridge.call("play", { action: "genuine", consent: true })).model_ready, true)
    assert.equal((await bridge.call("delete")).status, "deleted")
    assert.deepEqual(readdirSync(root), [])
    assert.equal((await bridge.call("play", { action: "genuine", consent: true })).status, "model_not_ready")
  } finally { await bridge.stop(); rmSync(root, { recursive: true, force: true }) }
})

test("logout cancels an in-flight worker and stale results cannot resolve as verification", async () => {
  const root = directory()
  const bridge = new BehaviorBridge(root)
  try {
    const pending = bridge.call("play", { action: "enroll-1", consent: true })
    const stopped = bridge.call("logout")
    assert.ok(["cancelled", "stopped"].includes((await pending).status))
    assert.equal((await stopped).status, "stopped")
    assert.equal(bridge.child, null)
    assert.deepEqual(readdirSync(root), [])
  } finally { await bridge.stop(); rmSync(root, { recursive: true, force: true }) }
})

test("pause clears pending enrollment and worker failure is sanitized", async () => {
  const root = directory()
  const bridge = new BehaviorBridge(root)
  try {
    await bridge.call("play", { action: "enroll-1", consent: true })
    await bridge.call("pause")
    const second = await bridge.call("play", { action: "enroll-2", consent: true })
    assert.equal(second.enrollment_sessions, 1)
    assert.equal(second.model_ready, false)
    await bridge.stop()
    const old = process.env.AEGIS_PYTHON
    process.env.AEGIS_PYTHON = path.join(root, "missing-python")
    try {
      assert.equal((await bridge.call("play", { action: "genuine", consent: true })).status, "bridge_unavailable")
    } finally {
      if (old === undefined) delete process.env.AEGIS_PYTHON
      else process.env.AEGIS_PYTHON = old
    }
  } finally { await bridge.stop(); rmSync(root, { recursive: true, force: true }) }
})
