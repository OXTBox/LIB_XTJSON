## LiveCode harvest data

This project works from a JSON export ("harvest") of LiveCode stacks, because LiveCode itself cannot be opened or run from the terminal. The harvest is the source of truth for the LiveCode GUI and scripts.

- Harvest output lives in `xtjson/XTJSON/` (original) and `xtjson/XTJSON_REBUILT/` (rebuilt copy). Start with `manifest.json`.
- The exporter is `xtjson/LCHarvest2.livecodescript` (LiveCode 9.6.3). It runs inside LiveCode only; the user runs it and copies the output here.
- Read `docs/harvest/XTJSON_ROUNDTRIP.md` first: it is the current state of the harvest -> rebuild -> diff work, which lives in `xtjson/`.
- Read `docs/harvest/HARVEST_FORMAT.md` before interpreting any harvest JSON.
- Read `docs/harvest/HARVESTER.md` before editing the exporter script or any LiveCode script.

Rules:

- Never hand-edit files under `XTJSON/` or `XTJSON_REBUILT/`. They are regenerated and a new harvest deletes the old one. To change the GUI or a script, write the change as LiveCode script for the user to apply, then ask for a fresh harvest.
- LiveCode code cannot be executed or compiled here. Say so when delivering LiveCode changes, and keep them small enough for the user to test one at a time.
- `props` in the harvest is sparse. Always resolve a property as: object `props` -> `typeDefaults[type]` in the manifest -> empty. Do not assume a missing property is false or zero without checking `typeDefaults`.
- Stack JSON files can be large. Query them with `jq` or a short Python script instead of reading whole files.
