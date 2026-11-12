# XTJSON round trip: state of work (2026-11-11)

Read this first when picking the work up in the terminal project. It records where the harvest -> rebuild -> re-harvest -> diff loop stands, how to run it, and what has been learned. `HARVEST_FORMAT.md` describes the JSON; `HARVESTER.md` describes the exporter and general LiveCode pitfalls.

## Goal

Prove the harvest is complete by rebuilding stacks from it and comparing. The same JSON will later drive generated Python / Raylib GUI code and the VibeCode3D engine work, so anything the rebuild cannot restore is something those generators will not know either.

## Files

| File | Role | State |
|---|---|---|
| `LCHarvest2.livecodescript` | harvester: stack -> JSON folder | compiles after fixes; first real harvest done by the user (output not yet seen here) |
| `LIB_XTJSON.livecodescript` | rebuild library: JSON folder -> stacks named `XT_<name>` | one rebuild run by the user before the layer fixes; current version not yet run |
| `xtReemder_Rebuild_stack.livecodescript` | launcher, a script-only stack with one button | refresh step reached by the user; rebuild step not yet confirmed |
| `xtjson_diff.py` | compares two harvest folders | tested here on synthetic data only |
| `xt_error_capture.livecodescript` | reads the IDE error window | untested |
| `revErrorDisplay_capture_card_script.livecodescript` | the user's own capture card script, verbatim, with its known problems listed in its header | the user's working test code |

None of the LiveCode scripts could be run where they were written. Treat every LiveCode behaviour described below as unverified unless marked confirmed.

## Working folder

Everything sits in one folder, beside the launcher:

```
xtReemder_Rebuild_stack.livecodescript
LIB_XTJSON.livecodescript
LCHarvest2.livecodescript
xtjson_diff.py
XTJSON/                 harvest of the original (the harvest output folder, renamed)
XTJSON_REBUILT/         harvest of the rebuilt copy, written by the launcher
XTJSON/rebuild_report.txt
xtjson_diff.txt
```

File names must be exact. Browser downloads create `name (1).ext` duplicates and stale copies; that already caused one false "file not found" and one "did not compile" from an old harvester copy.

## The loop

1. In the engine stack, with the current harvester: `harvestStack`, then copy/rename the output folder to `XTJSON`. The harvest must come from the current harvester, because only it writes `layer`.
2. Open `xtReemder_Rebuild_stack.livecodescript` (File > Open Stack) and click "Rebuild from XTJSON".
3. Read `XTJSON/rebuild_report.txt` (what the rebuild could not do).
4. `python3 xtjson_diff.py XTJSON XTJSON_REBUILT` and read `xtjson_diff.txt` (what differs after the round trip).
5. Fix harvester or rebuild library, repeat from 1 or 2.

## Launcher behaviour

- On open: creates button "Rebuild" on card 1.
- Refresh, on every click on card 1: reads `LIB_XTJSON.livecodescript` into the `XTJSON_SCRIPT` property of card 1; creates card "LIB_XTJSON" from the templateCard if missing; sets that card's script from the property. Same for the harvester with `XTHARVEST_SCRIPT` and card "LIB_XTHARVEST". So edits to the two library files take effect on the next click.
- Button: refresh, `dispatch "xtjsonRebuild"` to card "LIB_XTJSON" with the `XTJSON` folder, then `dispatch "harvestStack"` to card "LIB_XTHARVEST" for the rebuilt mainstack into `XTJSON_REBUILT`. Busy cursor throughout, arrow at the end. Summary goes to the message box.
- Clicking the card: refresh, then toggle between card 1 and card "LIB_XTJSON".
- It is a script-only stack: only the stack script is saved. Button, library cards and properties are recreated.

## Rebuild behaviour

- Builds `XT_<name>` stacks in memory, never saved. Substacks become substacks of the rebuilt mainstack. A second run deletes the previous `XT_` stacks first.
- Messages are locked during the build and when the rebuilt mainstack is opened.
- Per control: create (inside its group if it has one) -> restore id -> style -> content -> properties -> rect. Groups: lockLoc on, rect, properties, children, scroll, then lockLoc restored.
- Scripts and behaviors are applied after every object exists.
- Layers: controls are created back to front; `backgroundBehavior` and `sharedBehavior` are applied only after all cards exist; top-level controls are then put on their harvested layer with `set the layer`; every control's layer is verified.

Report kinds in `rebuild_report.txt`: `create`, `prop` (could not set), `differs` (set but reads back differently), `id`, `rect`, `layer-fixed` (creation order was wrong, corrected), `layer` (still wrong), `script`, `behavior`, `asset`, `place`, `custom`, `blob`, `json`, `fatal`.

## Findings so far

- Stack script round trip: the reassembled engine stack script matched the original apart from later additions by the user. Script export and restore are byte-faithful for that script. (Confirmed by diff.)
- First rebuild had scrambled layers. Probable cause: group "Viewport" has `backgroundBehavior` true, and LiveCode puts a background group on every card created afterwards, at the bottom, before the rebuild placed it at its harvested position. Fixed by deferring `backgroundBehavior`; not yet re-run.
- `set the layer` fails for grouped controls and for cards that are not open: "Object: can't set layer (card not open, or control in group)". Order inside a group can only come from creation order or `relayer ... to front of group`. If grouped layers still come out wrong, switch group filling to the engine's own method: create on the card, `relayer control id N to front of <group>`, then restore the control's rect.
- The rebuilt copy is live. Divide-by-zero errors were reported in card "Play.Canyon" (`sProjK` is 0 in `Game.OnStart` and `Canyon.UpdateShip`). Probable cause: handlers running in the rebuilt copy, or in the original while the copy was the current stack, without the engine's initialisation having set the projection values. Which stack raised them is not confirmed. The launcher harvests the copy before anything can run in it, so these do not affect the diff, but do not judge the rebuild by how the copy behaves when played.
- The engine keeps a frame loop running (`game.loop.tick`, sent to the stack). A harvest of the original taken while it runs includes graphics the engine created at runtime.

## Reading LiveCode errors

- Compile errors reported by `the result` after `set the script`: one line per frame, `error code,line,column,token`. Example `219,559,15,tExt` = line 559, column 15, at `tExt`.
- The line number refers to the script that was being set. The launcher's message says which ("LIB_XTJSON did not compile" / "the harvester did not compile").
- Execution errors appear in the IDE stack "revErrorDisplay", path at runtime: `.../LiveCode Community 9.6.3/Toolset/palettes/reverrordisplay.livecodescript`, text in fields inside `group id 1003 of card id 1002`. The fields are locked. `xt_error_capture.livecodescript` reads them: `put xtErrorCapture()`. It checks that the stack exists and reads fields only.

## Errors seen on 2026-11-11 and what they were

| Error | Source | Meaning |
|---|---|---|
| `Chunk: error in object expression`, line `set the customPropertySet ofrd to empty`, hint `ofrd` | the user's capture card script, an earlier version | a typo for `of card`; not in the harvester, library or launcher |
| `Object: does not have this property`, line `put the text of control i of gStack ...`, hint `captureStackText` | the user's capture card script, before the `try` was added | a control that is not a field or button has no `text` |
| `numeric: divide by zero`, object `Play.Canyon`, `sProjK` in `Game.OnStart` and `Canyon.UpdateShip` | the engine's card script | `sProjK` was 0: the game handlers ran before the projection values were set. Probably the rebuilt copy being live; not confirmed which stack raised it |
| `219,559,15,tExt` (three frames) | old copy of the harvester | `tExt` is the keyword `text`; fixed by renaming to `tSuffix` |

## Pitfalls met in this work (add to the list in HARVESTER.md as they occur)

- LiveCode is case-insensitive, so `tExt` is the keyword `text`. Any prefix + word that spells a LiveCode term is illegal as a variable: `tExt`, `tOp`, `tAb`, `tIme`, `tItle`, `sEt`, `sIze`, `pUt`. Use `tSuffix`, `tTopEdge` and so on.
- One-line `if ... then x` directly before `else` inside a block steals the `else`.
- `go` needs a literal `stack` keyword: `go card 1 of stack tName`, not `go card 1 of tStackRef`.
- Dynamic property names and uncertain syntax go through `do "..."` inside `try`, so they fail at run time, not at compile time.
- Asking a control that is not a field or button for `the text` raises "Object: does not have this property". Check `word 1 of the name` first.
- Putting a value into `tArr[i]` and then into `tArr[i]["key"]` replaces the first value: an element is either a value or an array.
- Code placed after a loop that `return`s on success only runs on failure; a log written there stays empty when things work.

## Open questions for the next run

1. Does the rebuild now finish, and what do the counts in `rebuild_report.txt` show (harvested vs rebuilt)?
2. Are there `layer` lines left, and are they for grouped or top-level controls?
3. Which properties dominate `prop` / `differs`? Those are candidates for the harvester's skip list or for special handling.
4. Were ids preserved (`id` lines)? Icons, behaviors and scripts depend on them.
5. Do `JsonImport` results come through for all files (`json` lines)?

## After the round trip is clean

- Write the launcher and libraries out into the harvest folder automatically when harvesting.
- Add options to the launcher (prefix, which stacks, whether to re-harvest).
- Decide whether to drop the `XT_` prefix when the original is not loaded.
- Start the Python / Raylib GUI generator from the same JSON.
