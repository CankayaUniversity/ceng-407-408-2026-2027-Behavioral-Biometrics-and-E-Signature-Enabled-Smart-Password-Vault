const { spawn } = require("node:child_process")
const { createInterface } = require("node:readline")
const path = require("node:path")
const fs = require("node:fs")
const repository = path.resolve(__dirname, "../../../../..")

class BehaviorBridge {
  constructor(directory) {
    this.directory = directory
    this.child = null
    this.pending = null
    this.stopping = Promise.resolve()
    this.epoch = 0
  }
  start() {
    const local = path.join(repository, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python")
    const python = process.env.AEGIS_PYTHON || (fs.existsSync(local) ? local : process.platform === "win32" ? "python" : "python3")
    const child = spawn(python, ["-u", "-m", "apps.desktop.services.behavior_worker", this.directory], {
      cwd: repository, stdio: ["pipe", "pipe", "ignore"], windowsHide: true,
    })
    this.child = child
    createInterface({ input: child.stdout }).on("line", line => {
      if (this.child !== child || !this.pending) return
      try {
        const result = JSON.parse(line)
        if (result.schema_version !== 1 || result.feature_version !== "timing-summary-v2" ||
            result.window_size !== 100 || result.model_version !== "standardized-rms-v1" ||
            typeof result.status !== "string" ||
            ![null, "synthetic-playback"].includes(result.source)) throw new Error()
        if (result.verification &&
            (typeof result.verification.accepted !== "boolean" ||
             (result.verification.distance !== null &&
              (!Number.isFinite(result.verification.distance) || result.verification.distance < 0)) ||
             (result.verification.threshold !== null &&
              (!Number.isFinite(result.verification.threshold) || result.verification.threshold < 0)))) throw new Error()
        this.pending.resolve(result)
      } catch { this.stop("bridge_error") }
    })
    const failed = () => { if (this.child === child) this.stop("bridge_unavailable") }
    child.on("error", failed)
    child.on("exit", failed)
    child.stdin.on("error", failed)
  }
  async call(command, data) {
    // Cancellation is never queued behind an in-flight playback.
    if (command === "logout" || command === "pause") {
      await this.stop(command === "logout" ? "stopped" : "paused")
      return Promise.resolve({ status: command === "logout" ? "stopped" : "paused" })
    }
    if (command === "delete") this.stop()
    const epoch = this.epoch
    await this.stopping
    if (epoch !== this.epoch) return { status: "cancelled" }
    if (this.pending) return Promise.resolve({ status: "busy" })
    if (!this.child) this.start()
    return new Promise(resolve => {
      const timer = setTimeout(() => this.stop("bridge_timeout"), 5000)
      this.pending = { resolve: value => { clearTimeout(timer); this.pending = null; resolve(value) } }
      this.child.stdin.write(JSON.stringify({ command, data }) + "\n")
    })
  }
  stop(status = "stopped") {
    this.epoch++
    const child = this.child
    this.child = null
    this.pending?.resolve({ status })
    if (child) {
      this.stopping = new Promise(resolve => child.once("close", resolve))
      child.kill()
    }
    return this.stopping
  }
}
module.exports = { BehaviorBridge }
