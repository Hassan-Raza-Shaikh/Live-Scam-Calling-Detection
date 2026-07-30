import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('sentinelDesktop', {
  sendAudioStream: (data: ArrayBuffer) => ipcRenderer.send('audio-stream', data),
  onAlertTriggered: (callback: (data: any) => void) => ipcRenderer.on('alert-triggered', (_event, value) => callback(value))
});
