import express from "express";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const statePath = path.join(__dirname, "data", "state.json");
const port = Number(process.env.PORT || 5173);
const app = express();

app.use(express.json());

async function readState() {
  const raw = await fs.readFile(statePath, "utf8");
  return JSON.parse(raw);
}

async function writeState(nextState) {
  await fs.mkdir(path.dirname(statePath), { recursive: true });
  await fs.writeFile(statePath, `${JSON.stringify(nextState, null, 2)}\n`);
  return nextState;
}

app.get("/api/state", async (_req, res) => {
  res.json(await readState());
});

app.put("/api/state", async (req, res) => {
  const current = await readState();
  const body = req.body || {};
  const next = {
    ...current,
    ...body,
    manual: Array.isArray(body.manual) ? body.manual.slice(0, 4).map(Number) : current.manual,
    selectedAxis: Number.isFinite(Number(body.selectedAxis)) ? Number(body.selectedAxis) : current.selectedAxis
  };
  res.json(await writeState(next));
});

app.post("/api/command", async (req, res) => {
  const state = await readState();
  const command = String(req.body?.command || "stop");
  const next = {
    ...state,
    lastCommand: command,
    updatedAt: new Date().toISOString()
  };
  res.json(await writeState(next));
});

if (process.env.NODE_ENV === "production") {
  app.use(express.static(path.join(__dirname, "dist")));
  app.get("*", (_req, res) => {
    res.sendFile(path.join(__dirname, "dist", "index.html"));
  });
} else {
  const { createServer } = await import("vite");
  const vite = await createServer({
    server: { middlewareMode: true },
    appType: "spa",
    root: __dirname
  });
  app.use(vite.middlewares);
}

app.listen(port, "0.0.0.0", () => {
  console.log(`Robot web app: http://localhost:${port}`);
});
