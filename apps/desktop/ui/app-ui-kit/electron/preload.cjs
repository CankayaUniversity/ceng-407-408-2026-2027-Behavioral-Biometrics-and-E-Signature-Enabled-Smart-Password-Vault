const { contextBridge, ipcRenderer } = require("electron")

contextBridge.exposeInMainWorld("enrollment", {
  register: (data) => ipcRenderer.invoke("enrollment:register", data),
  complete: () => ipcRenderer.invoke("enrollment:complete"),
  cancel: () => ipcRenderer.invoke("enrollment:cancel"),
})
