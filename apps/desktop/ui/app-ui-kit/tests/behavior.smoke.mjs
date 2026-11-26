// Real Electron + Python playback, with an isolated app data directory.
import { _electron as electron } from "playwright"
import { mkdtempSync, writeFileSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import path from "node:path"
import { fileURLToPath } from "node:url"
import assert from "node:assert/strict"
const kit = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const temporary = mkdtempSync(path.join(tmpdir(), "aegis-behavior-ui-"))
const entry = path.join(temporary, "launch.cjs")
writeFileSync(entry, `const {app}=require("electron");\napp.setPath("userData", ${JSON.stringify(path.join(temporary, "profile"))});\nrequire(${JSON.stringify(path.join(kit, "electron/main.cjs"))});\n`)
const env = { ...process.env }
delete env.ELECTRON_RUN_AS_NODE
let desktop
try {
  desktop = await electron.launch({ args: [entry], env })
  const page = await desktop.firstWindow()
  const errors = []
  page.on("pageerror", error => errors.push(error.message))
  await page.getByRole("button", { name: "Security Status", exact: true }).click()
  const panel = page.getByRole("region", { name: "Behavioral verification demonstration" })
  const record1 = panel.getByRole("button", { name: "Record session 1", exact: true })
  assert.equal(await record1.isDisabled(), true)
  await panel.getByRole("checkbox").check()
  await panel.getByRole("button", { name: "Replay genuine window" }).click()
  await panel.getByRole("status").filter({ hasText: "model_not_ready" }).waitFor()
  await record1.click()
  await panel.getByRole("status").filter({ hasText: "enrollment_recorded" }).waitFor()
  await panel.getByRole("button", { name: "Record session 2" }).click()
  await panel.getByRole("status").filter({ hasText: "Status: ready" }).waitFor()
  await panel.getByRole("button", { name: "Replay genuine window" }).click()
  await panel.getByRole("status").filter({ hasText: "observation: match;" }).waitFor()
  await panel.getByRole("button", { name: "Replay impostor window" }).click()
  await panel.getByRole("status").filter({ hasText: "behavior_mismatch" }).waitFor()
  await page.screenshot({ path: path.join(temporary, "behavior.png"), fullPage: true })
  await panel.getByRole("checkbox").uncheck()
  await panel.getByRole("status").filter({ hasText: "stopped" }).waitFor()
  assert.equal(await record1.isDisabled(), true)
  await panel.getByRole("button", { name: "Delete demo profile" }).click()
  await panel.getByRole("status").filter({ hasText: "deleted" }).waitFor()
  await panel.getByRole("checkbox").check()
  await panel.getByRole("button", { name: "Replay genuine window" }).click()
  await panel.getByRole("status").filter({ hasText: "model_not_ready" }).waitFor()
  await page.getByRole("button", { name: "Dashboard", exact: true }).click()
  await page.getByRole("button", { name: "Security Status", exact: true }).click()
  assert.equal(await panel.getByRole("checkbox").isChecked(), false)
  assert.deepEqual(errors, [])
  console.log(`Electron + Python behavior playback passed. Screenshot: ${temporary}/behavior.png`)
} finally {
  await desktop?.close()
  rmSync(path.join(temporary, "profile"), { recursive: true, force: true })
  rmSync(entry, { force: true })
}
