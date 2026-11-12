# LIB_XTJSON: notes for Claude Code

Read `README.md`, then `docs/CLAUDE_harvest_section.md` (rules for working with harvest
data: never hand-edit harvest output, resolve sparse props through typeDefaults, query
big JSON with a script, not by reading it whole) and `docs/XTJSON_ROUNDTRIP.md`.

- This library is built for AI agents (the owner's words: "built for YOU"). Keep the
  format readable and documented in `docs/HARVEST_FORMAT.md` whenever it changes.
- Compile-check every LiveCode change: `~/projects/LIB_MCP/tools/lcmcp compile <file>`.
- The owner finds raw JSON overwhelming: report findings as short tables and plain words.
- Harvest data of the owner's stacks lives in his working folders (`~/projects/XTJSON`,
  `~/projects/Vibecode3D/XTJSON`), not in this repository.
