import { test } from "node:test"
import assert from "node:assert/strict"
import { EnrollmentController } from "../apps/web/src/enrollment/controller.ts"
import { createMockService } from "../apps/web/src/enrollment/service.ts"

const input = {
  displayName: "Example",
  deviceId: "device-1",
  fingerSlot: "right_index",
}
const snapshot = {
  userId: "user-1",
  deviceId: "device-1",
  fingerSlot: "right_index",
  registered: true,
  enrolled: false,
  paired: false,
  pairingStatus: null,
  uncertain: false,
}

test("duplicate submits and safe retry do not create another user", async () => {
  let registrations = 0
  let completions = 0
  const controller = new EnrollmentController({
    async register() {
      registrations++
      return { snapshot, error: null, retryable: false }
    },
    async complete() {
      completions++
      return completions === 1
        ? { snapshot, error: "DISCONNECTED", retryable: true }
        : {
            snapshot: {
              ...snapshot,
              enrolled: true,
              paired: true,
              pairingStatus: "PENDING",
            },
            error: null,
            retryable: false,
          }
    },
    async cancel() {},
  })
  await Promise.all([controller.run(input), controller.run(input)])
  assert.equal(controller.getSnapshot().status, "error")
  await controller.run(input)
  assert.equal(controller.getSnapshot().status, "success")
  assert.equal(registrations, 1)
  assert.equal(completions, 2)
})

test("late registration response after cancel cannot trigger device enrollment", async () => {
  let finish
  let completions = 0
  const controller = new EnrollmentController({
    register() {
      return new Promise((resolve) => {
        finish = resolve
      })
    },
    async complete() {
      completions++
      return { error: null, retryable: false }
    },
    async cancel() {},
  })
  const pending = controller.run(input)
  await controller.cancel()
  finish({ snapshot, error: null, retryable: false })
  await pending
  assert.equal(controller.getSnapshot().status, "cancelled")
  assert.equal(completions, 0)
})

test("late device response cannot overwrite cancelled state", async () => {
  let finish
  const controller = new EnrollmentController({
    async register() {
      return { snapshot, error: null, retryable: false }
    },
    complete() {
      return new Promise((resolve) => {
        finish = resolve
      })
    },
    async cancel() {},
  })
  const pending = controller.run(input)
  await new Promise((resolve) => setImmediate(resolve))
  await controller.cancel()
  finish({
    snapshot: { ...snapshot, paired: true },
    error: null,
    retryable: false,
  })
  await pending
  assert.equal(controller.getSnapshot().status, "cancelled")
  assert.equal(controller.getSnapshot().snapshot.paired, false)
})

test("invalid form never calls services", async () => {
  let called = false
  const controller = new EnrollmentController({
    async register() {
      called = true
      return { error: null, retryable: false }
    },
    async complete() {
      called = true
      return { error: null, retryable: false }
    },
    async cancel() {},
  })
  await controller.run({ ...input, displayName: " " })
  assert.equal(controller.getSnapshot().error, "VALIDATION_ERROR")
  assert.equal(called, false)
})

for (const [scenario, error, retryable] of [
  ["success", null, false],
  ["duplicate", "DEVICE_ALREADY_REGISTERED", false],
  ["rejection", "DEVICE_REJECTED", true],
  ["disconnect", "DISCONNECTED", true],
  ["timeout", "OUTCOME_UNKNOWN", false],
  ["expired", "PAIRING_EXPIRED", false],
]) {
  test(`deterministic ${scenario} scenario`, async () => {
    const controller = new EnrollmentController(createMockService(scenario))
    await controller.run(input)
    assert.equal(controller.getSnapshot().error, error)
    assert.equal(controller.getSnapshot().retryable, retryable)
    if (retryable) {
      await controller.run(input)
      assert.equal(controller.getSnapshot().status, "success")
    } else if (error) {
      await controller.run(input)
      assert.equal(controller.getSnapshot().status, "error")
    }
  })
}
