// Runs the built Electron app against a disposable backend database.
import { _electron as electron } from "playwright"
import { spawn, execFileSync } from "node:child_process"
import { mkdtempSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import path from "node:path"
import { fileURLToPath } from "node:url"
import assert from "node:assert/strict"

const kit = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const repository = path.resolve(kit, "../../../..")
const python =
  process.env.AEGIS_PYTHON ||
  path.join(
    repository,
    ".venv",
    process.platform === "win32" ? "Scripts/python.exe" : "bin/python"
  )
const temporary = mkdtempSync(path.join(tmpdir(), "aegis-enrollment-"))
const env = {
  ...process.env,
  DATABASE_URL: `sqlite:///${path.join(temporary, "test.db")}`,
  AEGIS_PYTHON: python,
}
delete env.ELECTRON_RUN_AS_NODE
let backend
let desktop
try {
  execFileSync(python, ["-m", "services.backend.app.database.init_db"], {
    cwd: repository,
    env,
  })
  backend = spawn(
    python,
    [
      "-m",
      "uvicorn",
      "services.backend.app.main:app",
      "--host",
      "127.0.0.1",
      "--port",
      "8000",
    ],
    { cwd: repository, env, stdio: ["ignore", "ignore", "pipe"] }
  )
  await new Promise((resolve, reject) => {
    const timer = setTimeout(
      () => reject(new Error("Disposable backend did not start")),
      10000
    )
    backend.on("error", reject)
    backend.on("exit", () => {
      clearTimeout(timer)
      reject(new Error("Port 8000 unavailable or backend startup failed"))
    })
    backend.stderr.on("data", (chunk) => {
      if (chunk.toString().includes("Uvicorn running")) {
        clearTimeout(timer)
        resolve()
      }
    })
  })
  desktop = await electron.launch({
    args: [path.join(kit, "electron/main.cjs")],
    env,
  })
  const page = await desktop.firstWindow()
  const errors = []
  page.on("pageerror", (error) => errors.push(error.message))
  await page
    .getByRole("button", { name: "Create user and enroll device" })
    .click()
  await page
    .getByLabel("Display name", { exact: true })
    .fill("Desktop smoke user")
  await page.getByRole("button", { name: "Continue", exact: true }).click()
  await page
    .getByLabel("Simulated device ID", { exact: true })
    .fill("smoke-device-001")
  await page
    .getByLabel("Finger slot", { exact: true })
    .selectOption("left_thumb")
  await page.getByRole("button", { name: "Continue", exact: true }).click()
  await page
    .getByRole("button", { name: "Start enrollment", exact: true })
    .click()
  await page
    .getByRole("status")
    .filter({ hasText: "Enrollment steps completed" })
    .waitFor()
  assert.match(
    await page
      .getByRole("status")
      .filter({ hasText: "Enrollment steps completed" })
      .innerText(),
    /PENDING/
  )
  await page
    .getByText("No authenticated session was created.", { exact: false })
    .waitFor()
  await page.screenshot({
    path: path.join(temporary, "enrollment.png"),
    fullPage: true,
  })
  console.log(
    `Real backend + Python + Electron flow passed. Screenshot: ${temporary}/enrollment.png`
  )

  // Switching pages preserves the result and does not register another user.
  await page.getByRole("button", { name: "Dashboard", exact: true }).click()
  await page.getByRole("button", { name: "Enrollment", exact: true }).click()
  await page
    .getByRole("status")
    .filter({ hasText: "Enrollment steps completed" })
    .waitFor()
  const counts = execFileSync(
    python,
    [
      "-c",
      "from services.backend.app.database.connection import engine; from sqlalchemy import text; c=engine.connect(); print(c.execute(text('select count(*) from users')).scalar(), c.execute(text('select count(*) from devices')).scalar())",
    ],
    { cwd: repository, env }
  )
    .toString()
    .trim()
  assert.equal(counts, "1 1")
  assert.deepEqual(errors, [])
  console.log(
    "Navigation retained state; exactly one user and device created; no renderer errors."
  )

  // Exercise UI validation, partial errors, retries and the modal keyboard path.
  async function mockAttempt(scenario) {
    await page.getByRole("button", { name: "Start a new enrollment" }).click()
    await page.getByRole("combobox", { name: /^Service/ }).selectOption("mock")
    await page
      .getByRole("combobox", { name: /^Demo scenario/ })
      .selectOption(scenario)
    await page.getByRole("button", { name: "Continue", exact: true }).click()
    assert.equal(await page.locator("#display-name:invalid").count(), 1)
    await page.getByLabel("Display name", { exact: true }).fill("Mock user")
    await page.getByRole("button", { name: "Continue", exact: true }).click()
    await page
      .getByLabel("Simulated device ID", { exact: true })
      .fill("mock-device")
    await page.getByRole("button", { name: "Back", exact: true }).click()
    assert.equal(
      await page.getByLabel("Display name", { exact: true }).inputValue(),
      "Mock user"
    )
    await page.getByRole("button", { name: "Continue", exact: true }).click()
    await page.getByRole("button", { name: "Continue", exact: true }).click()
    await page
      .getByRole("button", { name: "Start enrollment", exact: true })
      .click()
  }
  await mockAttempt("duplicate")
  await page
    .getByRole("alert")
    .filter({ hasText: "already registered" })
    .waitFor()
  assert.equal(
    await page.getByRole("button", { name: "Retry failed step" }).count(),
    0
  )
  await mockAttempt("disconnect")
  await page.getByRole("button", { name: "Retry failed step" }).click()
  await page
    .getByRole("status")
    .filter({ hasText: "Enrollment steps completed" })
    .waitFor()
  await mockAttempt("timeout")
  await page
    .getByRole("alert")
    .filter({ hasText: "could not be confirmed" })
    .waitFor()
  await page
    .getByRole("button", { name: "Cancel enrollment", exact: true })
    .click()
  const modal = page.getByRole("dialog", { name: "Cancel enrollment?" })
  await modal.waitFor()
  assert.equal(
    await page.evaluate(() => document.activeElement.textContent),
    "Keep enrolling"
  )
  await page.keyboard.press("Escape")
  await modal.waitFor({ state: "hidden" })
  await page
    .getByRole("button", { name: "Cancel enrollment", exact: true })
    .click()
  await page.getByRole("button", { name: "Confirm cancellation" }).click()
  await page
    .getByRole("status")
    .filter({ hasText: "Enrollment cancelled" })
    .waitFor()
  assert.deepEqual(errors, [])
  console.log(
    "UI validation, back navigation, duplicate error, retry, timeout and cancellation passed."
  )
} catch (error) {
  if (desktop) {
    const page = await desktop.firstWindow()
    await page.screenshot({
      path: path.join(temporary, "failure.png"),
      fullPage: true,
    })
    console.error(`Failure screenshot: ${temporary}/failure.png`)
  }
  throw error
} finally {
  await desktop?.close()
  backend?.kill()
  // Keep only the screenshot for inspection; no key material is persisted.
  for (const name of [
    "test.db",
    "test.db-journal",
    "test.db-wal",
    "test.db-shm",
  ])
    rmSync(path.join(temporary, name), { force: true })
}
