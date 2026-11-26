const { contextBridge, ipcRenderer } = require("electron")

contextBridge.exposeInMainWorld("enrollment", {
  register: (data) => ipcRenderer.invoke("enrollment:register", data),
  complete: () => ipcRenderer.invoke("enrollment:complete"),
  cancel: () => ipcRenderer.invoke("enrollment:cancel"),
})

contextBridge.exposeInMainWorld("behavior", {
  play: (action, consent) => ipcRenderer.invoke("behavior:play", { action, consent }),
  pause: () => ipcRenderer.invoke("behavior:pause"),
  logout: () => ipcRenderer.invoke("behavior:logout"),
  deleteProfile: () => ipcRenderer.invoke("behavior:delete"),
})
