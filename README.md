# LIB_XTJSON

LiveCode stacks <-> JSON. Built for AI agents and code generators: a stack's cards,
controls, properties, custom properties and scripts as plain files that any tool can
read, plus a rebuild back into LiveCode and a diff that proves nothing was lost.

`.livecode` files are binary and only LiveCode reads them. While LiveCode 9.6.3 still
runs, a harvest turns every stack into data that outlives it (see `xtalk_py`).

| Path | What it is |
|---|---|
| `livecode/LCHarvest2.livecodescript` | Harvester: stack -> `manifest.json`, `stack_<Name>.json`, `scripts/`, `assets/`, `blobs/` |
| `livecode/LIB_XTJSON.livecodescript` | Rebuilder: harvest folder -> `XT_<name>` stacks in memory, with `rebuild_report.txt` |
| `livecode/xtReemder_Rebuild_stack.livecodescript` | Launcher (script-only stack): one button runs rebuild, then re-harvests the copy |
| `livecode/xt_error_capture.livecodescript` | Reads the IDE's error window (also built into LIB_MCP's error log) |
| `livecode/XTJSON_Batch.livecodescript` | **Batch app** (script-only stack, builds its own window): one click harvests every stack waiting in `~/projects/LIB_LLMIN/LIB_XTJSON` (any depth) into `~/projects/XTJSON/batch/<same path>/` and moves each original to `~/projects/LIB_LLMOUT/LIB_XTJSON/`. Log: `XTJSON/batch/_batch_log.tsv`; failures stay in the inbox, a stack that crashes the engine is skipped next time |
| `python/xtjson_diff.py` | Compares two harvests (original vs rebuilt), resolving sparse properties |
| `python/xtjson_harvest.py` | Harvest a stack file from a terminal (through LIB_MCP), and plain-text questions about a harvest: summary, handlers, globals, custom, script |
| `mcp/xtjson_tools.py` | MCP tool pack for LIB_MCP's server: `xtjson_harvest`, `xtjson_summary`, `xtjson_handlers`, `xtjson_globals`, `xtjson_custom`, `xtjson_script` |
| `docs/HARVEST_FORMAT.md` | The JSON format: read before interpreting a harvest |
| `docs/HARVESTER.md` | Using and changing the harvester; LiveCode pitfalls |
| `docs/XTJSON_ROUNDTRIP.md` | State of the harvest -> rebuild -> diff work and its findings |
| `reference/` | The owner's original error-capture card script, kept for reference |

## Use

**A pile of stacks (the usual way, 2026-11-13):** drop them anywhere under
`~/projects/LIB_LLMIN/LIB_XTJSON/`, open `livecode/XTJSON_Batch.livecodescript` in LiveCode (the
IDE, or the LIB_MCP standalone: `lcmcp --standalone run 'go stack "//wsl$/Ubuntu/home/igame3d/projects/LIB_XTJSON/livecode/XTJSON_Batch.livecodescript"'`)
and press **Run**. It lists every stack with its size and state, then works through them
one by one. Stop finishes the current stack; Run carries on later from where it stopped.
Stacks over 2 MB are harvested with their custom property data sampled (first 5 entries:
`customSample`, see docs/HARVEST_FORMAT.md). A stack that crashes LiveCode is retried once,
sampled, at the end of the run. To run unattended, start it with the watchdog:
`bash tools/xtjson_batch_watch.sh` (restarts LiveCode when a stack hangs for 5 minutes).


From a terminal, with the LIB_MCP standalone (started when needed) or IDE server:

```
~/projects/LIB_MCP/tools/lcmcp harvest path/to/Stack.livecode [OUTFOLDER]
python3 python/xtjson_harvest.py summary  <harvest>          # then: handlers / globals / custom / script
```

`OUTFOLDER` defaults to `~/projects/XTJSON/<file name>`; `<harvest>` may be that bare name.
The stack is loaded with messages locked (none of its handlers run), harvested, and removed
from memory again unless it was already open. Nothing is saved. The harvester is installed
as the script of a hidden stack `XT_HarvestLib` on every call, so edits to it apply at once.

For an MCP client (LM Studio, Claude Desktop):
`mcp_server.py --tools ~/projects/LIB_XTJSON/mcp/xtjson_tools.py` (see LIB_MCP's README).

By hand, in LiveCode:

In LiveCode: put `LCHarvest2.livecodescript` in a stack script, a library (`start using`)
or a behavior, then `harvestStack` and `put the result`. For the round trip, put the
launcher and the two libraries in one folder with the harvest renamed `XTJSON`, open the
launcher (File > Open Stack) and click "Rebuild from XTJSON". Then:

```
python3 python/xtjson_diff.py XTJSON XTJSON_REBUILT --prefix XT_
```

## Status

See `docs/XTJSON_ROUNDTRIP.md`. First full round trip done 2026-11-11 (owner's engine
stack): scripts restore byte-for-byte; open issues are the shared Viewport group not
being placed on other cards, hidden objects coming back visible, order inside groups,
and array custom properties.

Copied 2026-11-11 from the working folder `~/projects/XTJSON/xtjson` (the newest copies);
this repository is now the place to change them.

Part of the family of separate libraries listed in `~/projects/LIB_MCP/README.md`.
