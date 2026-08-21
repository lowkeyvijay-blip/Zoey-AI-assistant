const { app, BrowserWindow, ipcMain } = require("electron");
const { spawn } = require("child_process");
const http = require("http");
const path = require("path");
const fs = require("fs");

let mainWindow = null;
let backendProcess = null;

const BACKEND_PORT = parseInt(process.env.ZOEY_BACKEND_PORT || "8000", 10);
const BACKEND_HOST = "127.0.0.1";
const HEALTH_TIMEOUT = 15000;
const HEALTH_INTERVAL = 300;

function getBackendUrl() {
  return `http://${BACKEND_HOST}:${BACKEND_PORT}`;
}

function isDev() {
  return process.env.NODE_ENV === "development";
}

function getBackendExePath() {
  if (isDev()) return null;

  const resourcesPath = process.resourcesPath || path.join(__dirname, "..", "resources");
  return path.join(resourcesPath, "backend", "ZoeyBackend", "ZoeyBackend.exe");
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    title: "Zoey",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  if (isDev()) {
    mainWindow.loadURL("http://localhost:5173");
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else {
    mainWindow.loadURL(getBackendUrl());
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

function waitForBackend() {
  return new Promise((resolve, reject) => {
    const start = Date.now();

    function check() {
      const req = http.get(getBackendUrl() + "/api/health", (res) => {
        if (res.statusCode === 200) {
          resolve();
        } else {
          retryOrTimeout();
        }
        res.resume();
      });

      req.on("error", () => retryOrTimeout());
      req.setTimeout(2000, () => {
        req.destroy();
        retryOrTimeout();
      });
    }

    function retryOrTimeout() {
      if (Date.now() - start > HEALTH_TIMEOUT) {
        reject(new Error("Backend failed to start within timeout"));
      } else {
        setTimeout(check, HEALTH_INTERVAL);
      }
    }

    check();
  });
}

function startBackend() {
  const exePath = getBackendExePath();

  if (isDev()) {
    console.log("[Zoey] Starting Python backend (dev mode)");
    const repoRoot = path.resolve(__dirname, "..", "..");

    backendProcess = spawn("python", ["-m", "api.server"], {
      cwd: repoRoot,
      env: { ...process.env },
      stdio: ["ignore", "pipe", "pipe"],
    });
  } else {
    console.log("[Zoey] Starting bundled backend:", exePath);

    if (!fs.existsSync(exePath)) {
      console.error("[Zoey] Backend executable not found:", exePath);
      showBackendError(`Backend executable not found at:\n${exePath}`);
      return;
    }

    backendProcess = spawn(exePath, [], {
      env: { ...process.env },
      stdio: ["ignore", "pipe", "pipe"],
    });
  }

  if (!backendProcess) {
    return;
  }

  backendProcess.stdout.on("data", (data) => {
    console.log("[Zoey Backend]", data.toString().trim());
  });

  backendProcess.stderr.on("data", (data) => {
    console.log("[Zoey Backend]", data.toString().trim());
  });

  backendProcess.on("error", (err) => {
    console.error("[Zoey] Failed to start backend:", err.message);
    showBackendError(
      isDev()
        ? `Could not start the Python backend. Ensure Python is installed.\n${err.message}`
        : `Could not start the backend.\n${err.message}`
    );
  });

  backendProcess.on("exit", (code) => {
    console.log("[Zoey] Backend exited with code:", code);
    backendProcess = null;
  });
}

function showBackendError(message) {
  if (mainWindow) {
    const escaped = message.replace(/`/g, "\\`").replace(/\n/g, "<br>");
    mainWindow.webContents.executeJavaScript(`
      document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;background:#0a0a0f;color:#e0e0e0;font-family:system-ui;text-align:center;padding:2rem;"><div><h1 style="font-size:1.5rem;margin-bottom:1rem;">Backend Failed to Start</h1><p style="color:#888;">${escaped}</p></div></div>'
    `);
  }
}

function killBackend() {
  if (!backendProcess) return;

  console.log("[Zoey] Shutting down backend...");

  try {
    if (process.platform === "win32") {
      spawn("taskkill", ["/pid", String(backendProcess.pid), "/T", "/F"], {
        stdio: "ignore",
      });
    } else {
      backendProcess.kill("SIGTERM");
    }
  } catch {
    try {
      backendProcess.kill("SIGKILL");
    } catch {
      // Already dead
    }
  }

  backendProcess = null;
}

// IPC handlers
ipcMain.handle("get-backend-url", () => getBackendUrl());

// App lifecycle
app.whenReady().then(async () => {
  if (isDev()) {
    console.log("[Zoey] Development mode");
    createWindow();
  } else {
    console.log("[Zoey] Production mode");
    startBackend();

    try {
      await waitForBackend();
      console.log("[Zoey] Backend is healthy");
    } catch (err) {
      console.error("[Zoey]", err.message);
    }

    createWindow();
  }
});

app.on("window-all-closed", () => {
  killBackend();
  app.quit();
});

app.on("before-quit", () => {
  killBackend();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
