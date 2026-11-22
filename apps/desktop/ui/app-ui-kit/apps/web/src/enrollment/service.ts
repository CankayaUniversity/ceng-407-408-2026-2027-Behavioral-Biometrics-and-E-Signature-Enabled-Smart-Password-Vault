export type EnrollmentInput = {
  displayName: string
  deviceId: string
  fingerSlot: string
}
export type EnrollmentSnapshot = {
  userId: string | null
  deviceId: string | null
  fingerSlot: string | null
  registered: boolean
  enrolled: boolean
  paired: boolean
  pairingStatus: string | null
  uncertain: boolean
}
export type EnrollmentResult = {
  snapshot?: EnrollmentSnapshot
  error: string | null
  retryable: boolean
}
export interface EnrollmentService {
  register(data: EnrollmentInput): Promise<EnrollmentResult>
  complete(): Promise<EnrollmentResult>
  cancel(): Promise<void>
}

declare global {
  interface Window {
    enrollment?: EnrollmentService
  }
}

export const MOCK_SCENARIOS = [
  "success",
  "duplicate",
  "rejection",
  "disconnect",
  "timeout",
  "expired",
] as const
export type MockScenario = (typeof MOCK_SCENARIOS)[number]

export function createMockService(
  scenario: MockScenario = "success"
): EnrollmentService {
  let snapshot: EnrollmentSnapshot = {
    userId: null,
    deviceId: null,
    fingerSlot: null,
    registered: false,
    enrolled: false,
    paired: false,
    pairingStatus: null,
    uncertain: false,
  }
  let attempts = 0
  const respond = async (
    error: string | null = null,
    retryable = false
  ): Promise<EnrollmentResult> => {
    await new Promise((resolve) => setTimeout(resolve, 250))
    return { snapshot: { ...snapshot }, error, retryable }
  }
  return {
    async register(data) {
      snapshot = {
        ...snapshot,
        userId: "mock-user-001",
        deviceId: data.deviceId,
        fingerSlot: data.fingerSlot,
        registered: true,
      }
      return respond()
    },
    async complete() {
      attempts++
      if (scenario === "rejection" && attempts === 1)
        return respond("DEVICE_REJECTED", true)
      snapshot = { ...snapshot, enrolled: true }
      if (scenario === "duplicate") return respond("DEVICE_ALREADY_REGISTERED")
      if (scenario === "expired") return respond("PAIRING_EXPIRED")
      if (scenario === "disconnect" && attempts === 1)
        return respond("DISCONNECTED", true)
      if (scenario === "timeout") {
        snapshot = { ...snapshot, uncertain: true }
        return respond("OUTCOME_UNKNOWN")
      }
      snapshot = { ...snapshot, paired: true, pairingStatus: "PENDING" }
      return respond()
    },
    async cancel() {},
  }
}

export function desktopService(): EnrollmentService {
  const bridge = window.enrollment
  if (!bridge) throw new Error("Desktop bridge unavailable")
  return bridge
}
