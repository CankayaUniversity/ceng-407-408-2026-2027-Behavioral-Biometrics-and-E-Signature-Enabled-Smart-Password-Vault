const path = require("node:path");
const { app, BrowserWindow, ipcMain } = require("electron");
const { BehaviorBridge } = require("./behavior.cjs");
const { EnrollmentBridge } = require("./enrollment.cjs");
const { pathToFileURL } = require("node:url");

const DEV_URL = "http://127.0.0.1:5173";
const isDevelopment = !app.isPackaged && process.argv.includes("--dev");

function createWindow() {
  const enrollment = new EnrollmentBridge();
  const behavior = new BehaviorBridge(path.join(app.getPath("userData"), "behavioral-demo-profiles"));
  const window = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 960,
    minHeight: 640,
    title: "Aegis Vault",
    backgroundColor: "#090d17",
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
      preload: path.join(__dirname, "preload.cjs"),
    },
  });

  const builtUrl = pathToFileURL(path.join(__dirname, "../apps/web/dist/index.html")).href;
  function trusted(event) {
    return event.sender === window.webContents && event.senderFrame === window.webContents.mainFrame &&
      (isDevelopment ? event.senderFrame.url === DEV_URL + "/" : event.senderFrame.url === builtUrl);
  }
  for (const command of ["register", "complete", "cancel"]) {
    ipcMain.handle(`enrollment:${command}`, (event, data) => {
      if (!trusted(event)) throw new Error("Untrusted enrollment request");
      if (command === "cancel") {
        enrollment.stop();
        return;
      }
      if (command === "register" && (!data || typeof data !== "object" ||
          typeof data.displayName !== "string" || data.displayName.length > 100 ||
          typeof data.deviceId !== "string" || data.deviceId.length > 36 ||
          typeof data.fingerSlot !== "string" || data.fingerSlot.length > 20)) {
        return { error: "VALIDATION_ERROR", retryable: false };
      }
      return enrollment.call(command, command === "register" ? {
        displayName: data.displayName, deviceId: data.deviceId, fingerSlot: data.fingerSlot,
      } : undefined);
    });
  }
  for (const command of ["play", "pause", "logout", "delete"]) {
    ipcMain.handle(`behavior:${command}`, (event, data) => {
      if (!trusted(event)) throw new Error("Untrusted behavior request");
      if (command === "play") {
        if (!data || data.consent !== true ||
            !["enroll-1", "enroll-2", "genuine", "impostor"].includes(data.action)) {
          behavior.stop("consent_required");
          return { status: "consent_required" };
        }
        return behavior.call(command, { consent: true, action: data.action });
      }
      return behavior.call(command);
    });
  }
  window.on("closed", () => {
    enrollment.stop();
    behavior.stop();
    for (const command of ["play", "pause", "logout", "delete"]) ipcMain.removeHandler(`behavior:${command}`);
    for (const command of ["register", "complete", "cancel"]) ipcMain.removeHandler(`enrollment:${command}`);
  });

  window.setMenuBarVisibility(false);
  window.webContents.on("did-start-loading", () => { enrollment.stop(); behavior.stop(); });

  window.once("ready-to-show", () => {
    window.show();
  });

  window.webContents.setWindowOpenHandler(() => ({
    action: "deny",
  }));

  window.webContents.on("will-navigate", (event, url) => {
    if (isDevelopment && new URL(url).origin === DEV_URL) {
      return;
    }

    event.preventDefault();
  });

  window.webContents.session.setPermissionRequestHandler(
    (_webContents, _permission, callback) => {
      callback(false);
    },
  );

  window.webContents.session.setPermissionCheckHandler(() => false);

  const loading = isDevelopment
    ? window.loadURL(DEV_URL)
    : window.loadFile(
        path.join(__dirname, "../apps/web/dist/index.html"),
      );

  loading.catch((error) => {
    console.error("Unable to load the desktop interface:", error.message);
    app.quit();
  });
}

app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
