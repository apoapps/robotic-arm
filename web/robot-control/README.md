# Robot control web

Simple local UI for the PicoCalc robot project.

```sh
npm install
npm run dev
```

Open `http://localhost:5173`.

The UI stores state in `data/state.json`. To copy that state to PicoCalc:

```sh
../../tools/sync_web_state_to_picocalc.sh
```
