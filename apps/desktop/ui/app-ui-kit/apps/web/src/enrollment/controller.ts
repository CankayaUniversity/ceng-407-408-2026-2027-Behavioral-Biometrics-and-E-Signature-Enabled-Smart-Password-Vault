import type {
  EnrollmentInput,
  EnrollmentResult,
  EnrollmentService,
  EnrollmentSnapshot,
} from "./service.ts"

export type EnrollmentState = {
  status: "idle" | "running" | "error" | "success" | "cancelled"
  phase: "registration" | "device"
  snapshot?: EnrollmentSnapshot
  error: string | null
  retryable: boolean
}

export class EnrollmentController {
  private state: EnrollmentState = {
    status: "idle",
    phase: "registration",
    error: null,
    retryable: false,
  }
  private listeners = new Set<() => void>()
  private generation = 0
  private service: EnrollmentService

  constructor(service: EnrollmentService) {
    this.service = service
  }
  getSnapshot = () => this.state
  subscribe = (listener: () => void) => {
    this.listeners.add(listener)
    return () => {
      this.listeners.delete(listener)
    }
  }
  private publish(state: EnrollmentState) {
    this.state = state
    this.listeners.forEach((listener) => listener())
  }

  async run(input: EnrollmentInput) {
    if (
      this.state.status === "running" ||
      this.state.status === "success" ||
      this.state.status === "cancelled" ||
      (this.state.status === "error" && !this.state.retryable)
    )
      return
    if (
      !input.displayName.trim() ||
      input.displayName.trim().length > 100 ||
      !input.deviceId.trim() ||
      input.deviceId.trim().length > 36 ||
      !/^(left|right)_(thumb|index|middle|ring|little)$/.test(input.fingerSlot)
    ) {
      this.publish({
        ...this.state,
        status: "error",
        error: "VALIDATION_ERROR",
        retryable: true,
      })
      return
    }
    const generation = ++this.generation
    this.publish({
      ...this.state,
      status: "running",
      error: null,
      retryable: false,
    })
    const accept = (result: EnrollmentResult) => {
      if (generation !== this.generation) return false
      this.publish({
        ...this.state,
        snapshot: result.snapshot ?? this.state.snapshot,
        error: result.error,
        retryable: result.retryable,
        status: result.error ? "error" : "running",
      })
      return !result.error
    }
    try {
      if (!this.state.snapshot?.registered) {
        if (!accept(await this.service.register(input))) return
        if (!this.state.snapshot?.registered)
          throw new Error("Missing registration")
      }
      if (generation !== this.generation) return
      this.publish({ ...this.state, phase: "device" })
      if (!accept(await this.service.complete())) return
      if (!this.state.snapshot?.paired) throw new Error("Incomplete pairing")
      this.publish({ ...this.state, status: "success" })
    } catch {
      if (generation === this.generation)
        this.publish({
          ...this.state,
          status: "error",
          error: "OUTCOME_UNKNOWN",
          retryable: false,
        })
    }
  }

  async cancel() {
    ++this.generation
    this.publish({
      ...this.state,
      status: "cancelled",
      error: null,
      retryable: false,
    })
    try {
      await this.service.cancel()
    } catch {
      /* Cancellation cannot undo server writes. */
    }
  }
}
