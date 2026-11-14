const path = require("node:path");
const { app, BrowserWindow } = require("electron");

const DEV_URL = "http://127.0.0.1:5173";
const isDevelopment = !app.isPackaged && process.argv.includes("--dev");

function createWindow() {
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
    },
  });

  window.setMenuBarVisibility(false);

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