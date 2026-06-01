import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const axes = ["EE", "Q1", "Q2", "Q3"];
const axisNames = ["End effector", "Base", "Shoulder", "Elbow"];

const fallbackState = {
  move_ms: 250,
  step: 5,
  live: true,
  manual: [90, 90, 90, 90],
  selectedAxis: 0,
  lastCommand: "Ready"
};

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function App() {
  const [state, setState] = useState(fallbackState);
  const [status, setStatus] = useState("Loading");

  useEffect(() => {
    fetch("/api/state")
      .then((res) => res.json())
      .then((data) => {
        setState({ ...fallbackState, ...data });
        setStatus("Synced");
      })
      .catch(() => setStatus("Local only"));
  }, []);

  async function sync(next) {
    setState(next);
    try {
      const res = await fetch("/api/state", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(next)
      });
      setState(await res.json());
      setStatus("Synced");
    } catch {
      setStatus("Local only");
    }
  }

  async function command(name) {
    setStatus(name);
    try {
      const res = await fetch("/api/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: name })
      });
      setState(await res.json());
    } catch {
      setStatus("Command saved locally");
    }
  }

  const selected = clamp(Number(state.selectedAxis || 0), 0, 3);
  const commandPreview = useMemo(() => {
    const t = Number(state.move_ms || 250);
    return `<BUZZ,${state.manual.join(",")},${t},${t},${t},${t}>`;
  }, [state.manual, state.move_ms]);

  function setAxisValue(index, value) {
    const manual = [...state.manual];
    manual[index] = clamp(Number(value), 0, 180);
    sync({ ...state, manual });
  }

  function nudge(delta) {
    const manual = [...state.manual];
    manual[selected] = clamp(manual[selected] + delta * Number(state.step || 1), 0, 180);
    sync({ ...state, manual });
    command(`${axes[selected]} ${delta > 0 ? "forward" : "reverse"}`);
  }

  return (
    <main className="h-screen w-screen overflow-hidden bg-white text-black">
      <section className="grid h-full grid-rows-[auto_1fr_auto] border-4 border-black">
        <header className="flex items-center justify-between border-b-4 border-black px-4 py-3">
          <div>
            <h1 className="text-2xl font-black uppercase leading-none">Proyecto final Robotica</h1>
            <p className="text-sm uppercase">Apodaca, Calderon, Soriano, Ochoa</p>
          </div>
          <div className="text-right text-sm uppercase">
            <div>{status}</div>
            <div>PINS</div>
          </div>
        </header>

        <div className="grid min-h-0 grid-cols-1 md:grid-cols-[260px_1fr]">
          <nav className="border-b-4 border-black p-3 md:border-b-0 md:border-r-4">
            {["Dashboard", "Manual", "Connection", "Sync"].map((item) => (
              <button key={item} className="mb-2 block w-full border-2 border-black bg-white px-3 py-3 text-left text-lg font-bold">
                {item}
              </button>
            ))}
            <div className="mt-4 border-2 border-black p-3 text-sm">
              <div>Selected axis</div>
              <div className="text-2xl font-black">{axes[selected]}</div>
              <div>{axisNames[selected]}</div>
            </div>
          </nav>

          <div className="min-h-0 overflow-auto p-4">
            <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
              <section className="border-2 border-black p-4">
                <h2 className="mb-4 text-2xl font-black uppercase">Manual Control</h2>
                <div className="space-y-4">
                  {axes.map((axis, index) => (
                    <label key={axis} className={`block border-2 p-3 ${selected === index ? "border-black bg-black text-white" : "border-black bg-white"}`}>
                      <div className="mb-2 flex items-center justify-between">
                        <button
                          className="border-2 border-current px-3 py-1 font-black"
                          onClick={() => sync({ ...state, selectedAxis: index })}
                        >
                          {axis}
                        </button>
                        <span>{axisNames[index]}</span>
                        <span className="font-black">{state.manual[index]} deg</span>
                      </div>
                      <input
                        className="w-full accent-black"
                        type="range"
                        min="0"
                        max="180"
                        value={state.manual[index]}
                        onChange={(event) => setAxisValue(index, event.target.value)}
                      />
                    </label>
                  ))}
                </div>
              </section>

              <aside className="space-y-4">
                <section className="border-2 border-black p-4">
                  <h2 className="mb-3 text-xl font-black uppercase">Move</h2>
                  <div className="grid grid-cols-2 gap-2">
                    <button className="border-2 border-black py-4 font-black" onClick={() => nudge(-1)}>Reverse</button>
                    <button className="border-2 border-black py-4 font-black" onClick={() => nudge(1)}>Forward</button>
                    <button className="col-span-2 border-2 border-black py-4 font-black" onClick={() => command("stop")}>Stop</button>
                  </div>
                </section>

                <section className="border-2 border-black p-4">
                  <h2 className="mb-3 text-xl font-black uppercase">Settings</h2>
                  <label className="mb-3 block">
                    <span className="block text-sm uppercase">Pulse / time ms</span>
                    <input className="w-full border-2 border-black p-2" type="number" value={state.move_ms} onChange={(e) => sync({ ...state, move_ms: Number(e.target.value) })} />
                  </label>
                  <label className="block">
                    <span className="block text-sm uppercase">Step</span>
                    <input className="w-full border-2 border-black p-2" type="number" value={state.step} onChange={(e) => sync({ ...state, step: Number(e.target.value) })} />
                  </label>
                </section>

                <section className="border-2 border-black p-4">
                  <h2 className="mb-3 text-xl font-black uppercase">Sync</h2>
                  <pre className="whitespace-pre-wrap break-all border-2 border-black p-2 text-xs">{commandPreview}</pre>
                  <button className="mt-3 w-full border-2 border-black py-3 font-black" onClick={() => command(commandPreview)}>Save Command</button>
                </section>
              </aside>
            </div>
          </div>
        </div>

        <footer className="border-t-4 border-black px-4 py-2 text-sm uppercase">
          GPIO pins: EE 2/3 | Q1 4/5 | Q2 21/28 | Q3 8/9
        </footer>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
