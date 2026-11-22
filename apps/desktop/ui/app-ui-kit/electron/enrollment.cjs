const { spawn } = require("node:child_process")
const { createInterface } = require("node:readline")
const path = require("node:path")
const fs = require("node:fs")

const repository = path.resolve(__dirname, "../../../../..")

class EnrollmentBridge {
  constructor() {
    this.child = null
    this.pending = null
  }

  start() {
    const local = path.join(
      repository,
      ".venv",
      process.platform === "win32" ? "Scripts/python.exe" : "bin/python"
    )
    const python =
      process.env.AEGIS_PYTHON ||
      (fs.existsSync(local)
        ? local
        : process.platform === "win32"
          ? "python"
          : "python3")
    const child = spawn(
      python,
      ["-u", "-m", "apps.desktop.services.enrollment_worker"],
      {
        cwd: repository,
        stdio: ["pipe", "pipe", "ignore"],
        windowsHide: true,
      }
    )
    this.child = child
    const lines = createInterface({ input: child.stdout })
    lines.on("line", (line) => {
      if (this.child !== child || !this.pending) return
      try {
        const result = JSON.parse(line)
        this.pending.resolve(result)
      } catch {
        this.pending.resolve({ error: "OUTCOME_UNKNOWN", retryable: false })
        this.stop()
      }
    })
    const failed = () => {
      if (this.child !== child) return
      this.child = null
      this.pending?.resolve({ error: "BRIDGE_UNAVAILABLE", retryable: false })
    }
    child.on("error", failed)
    child.on("exit", failed)
    child.stdin.on("error", failed)
  }

  call(command, data) {
    if (this.pending)
      return Promise.resolve({ error: "BUSY", retryable: false })
    if (command === "register") {
      if (this.child)
        return Promise.resolve({ error: "ALREADY_STARTED", retryable: false })
      this.start()
    }
    if (!this.child)
      return Promise.resolve({ error: "BRIDGE_UNAVAILABLE", retryable: false })
    return new Promise((resolve) => {
      const timer = setTimeout(() => this.stop("OUTCOME_UNKNOWN"), 12000)
      this.pending = {
        resolve: (value) => {
          clearTimeout(timer)
          this.pending = null
          resolve(value)
        },
      }
      this.child.stdin.write(JSON.stringify({ command, data }) + "\n")
    })
  }

  stop(code = "CANCELLED") {
    const child = this.child
    this.child = null
    this.pending?.resolve({ error: code, retryable: false })
    child?.kill()
  }
}

module.exports = { EnrollmentBridge }
