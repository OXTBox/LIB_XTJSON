# The harvester script (LCHarvest2.livecodescript)

Notes for working on the exporter and on LiveCode script in general. Output format is described in `HARVEST_FORMAT.md`.

## Status

- Current state of the whole harvest / rebuild / diff loop is in `XTJSON_ROUNDTRIP.md`. Read that first.
- Written for LiveCode 9.6.3 without access to a LiveCode engine. It has been compiled by the user (one compile error found and fixed, see "LiveCode pitfalls"). Runtime behaviour is still being verified.
- Update this section as items under "Unverified" are confirmed or corrected.

## Running it (done by the user, inside LiveCode)

The script goes in a stack script, a library stack (`start using`), or a behavior.

```
harvestStack                      -- mainstack of the current stack + all substacks
put the result                    -- one-line summary with the output folder
put harvestErrors()               -- details if the summary reports errors
```

Full signatures:

| Call | Result |
|---|---|
| `harvestStack [stackName] [, outFolder] [, optionsArray]` | writes the whole harvest; summary in `the result` |
| `harvestCard [cardRef] [, outFolder] [, optionsArray]` | writes one self-contained `card_*.json`; path in `the result` |
| `harvestCardJSON([cardRef] [, optionsArray])` | returns JSON, writes nothing |
| `harvestControlJSON(controlRef [, optionsArray])` | returns JSON, writes nothing |
| `harvestTypeDefaultsJSON()` | returns the typeDefaults table as JSON |
| `harvestErrors()` | errors of the last run |

Default output folder: `<folder of the stack file>/Harvest/<MainStackName>`. The user copies that folder to `harvest/<MainStackName>/` in this project, or passes this project's folder as `outFolder`.

The three JSON-returning functions are meant for live use (MCP, message box). They return sparse `props`, so the caller needs `harvestTypeDefaultsJSON()` once per session.

## Options

| Key | Default | Effect |
|---|---|---|
| `scripts` | `"files"` | `"files"`, `"inline"` or `"none"`. Forced to `"inline"` when nothing is written to disk. |
| `handlerIndex` | true | list handlers with line numbers |
| `sparse` | true | write only props that differ from typeDefaults |
| `substacks` | true | false harvests only the named stack |
| `assets` | true | write embedded images and binary custom properties |
| `dedupeShared` | true | shared groups in full on the first card only |
| `ideProps` | false | true keeps `cREV*` custom properties |
| `clean` | true | delete the previous harvest in the output folder first |
| `maxInline` | 20000 | longer text goes to `blobs/`; 0 means always inline |
| `skipCustomKeys` | old harvester bookkeeping names | comma list of custom property names to ignore |

`clean` only empties a folder whose `manifest.json` contains the format marker, and only `scripts/`, `assets/`, `blobs/` and `stack_*.json`.

## How it works

- `beginHarvest` sets options and state, and calls `buildDefaults` once per session.
- `buildDefaults` creates an invisible temporary stack, creates one object of each type in it, records `the properties` of each, and deletes the stack. It does not reset the template objects, so typeDefaults reflect the session's current templates.
- `stackNode` -> `cardNode` -> `controlNode` build the JSON. Controls are addressed as `control id <n> of <card long id>` so that card context is kept for shared groups.
- Group nesting: `cardNode` walks `control 1..n` of the card (a flat, layer-ordered list). `controlNode` recurses through `the childControlIDs` of a group and marks every child in `sSeenOnCard`, so the card loop skips controls already written inside a group.
- Properties come from `the properties` of the object, filtered by `kSkipProps` and diffed against the defaults in `compactProps`.
- JSON is built as text by `jStr`, `jPair`, `jAdd`, `listAdd`, `jNode`, `jList`, `jArray`. No JSON library is used, so key order is fixed. Encoded strings never contain a raw line break, which is what lets `jNode` and `jList` indent nested blocks with a plain `replace cr`.
- Each stack, card and control is wrapped in `try`, so one bad object is logged to `sErrors` and skipped.

The exporter reads only. The single exception is in `customJSON`: if an object's active `customPropertySet` is not the default, it is switched to the default and back, under `lock messages`.

## Unverified

Check these against the first real harvest and record the outcome here.

- `the childControlIDs` of a group returns direct children. If groups show empty `controls` and their children appear at card level, this is the cause.
- `buildDefaults` succeeds in the IDE and in a standalone. If not, `errors` in the manifest says so and props are written in full.
- `the properties` of each object type includes everything a GUI generator needs. Properties it omits must be added explicitly in `controlNode`, the way `text`, `htmlText` and `points` already are.
- Painted images (no PNG/GIF/JPEG/BMP header) export through the `do "export image id ..."` fallback in `imageAssetJSON`.
- `the effective backgroundColor` and `foregroundColor` of a stack return a usable value.
- Widget properties export sensibly through `the properties`.

## LiveCode pitfalls (for any LiveCode script written in this project)

- A one-line `if x then y` followed directly by `else` on the next line: the `else` binds to the one-line `if`, not to an enclosing block. Inside a multi-line `if ... else ... end if`, never put a one-line `if` as the last statement before `else`. This caused the one compile error so far (`compactProps`).
- LiveCode is case-insensitive, so a variable such as `tExt` is the keyword `text` and will not compile. Avoid any prefix + word that spells a LiveCode term (`tOp`, `tAb`, `tIme`, `tItle`, `sEt`, `sIze`, `pUt`).
- `go` needs a literal `stack` keyword: `go card 1 of stack tName`. A stack reference in a variable is rejected ("No stack reference here").
- `set the layer` fails for controls inside a group and for cards that are not open. Inside a group, order comes from creation order or `relayer ... to front of group`.
- A group with `backgroundBehavior` true is put on every card created after it.
- `the text` of a control that is not a field or button raises "Object: does not have this property".
- Compile errors from `the result` read `error code,line,column,token`.
- A compile error anywhere disables the whole script. Syntax that might not compile goes inside `do "..."` within `try`, so a failure becomes a catchable runtime error.
- Built-in property names cannot be supplied from a variable: `the tProp of tObj` reads a custom property named by `tProp`. Use `the properties of tObj` and index the array.
- `the itemDelimiter` is local to a handler and resets to comma on entry. Set it in each handler that needs "/".
- Comparison with `is` is case-insensitive and numeric when both sides are numbers.
- Backslash is not an escape character in LiveCode string literals; `quote`, `cr`, `tab` are constants.
- `return x` in a command sets `the result` in the caller.
- All values are strings or arrays. An empty array is the empty string, so `is an array` is false for it.
- Script-local variables (`local sX` outside handlers) persist for the session and are reset when the script is recompiled.

## Changing the exporter

- Changes to output shape require: bump `kFormatVersion`, update `conventionsJSON` in the script, update `HARVEST_FORMAT.md`.
- New property handling goes in `controlNode` (explicit keys) or the constants `kSkipProps` / `kStringProps`.
- Keep the exporter read-only with respect to the harvested stack.
- Deliver changes as small, separately testable edits, since nothing here can compile or run LiveCode.

## History

- 2007: iGame3D_UI_Main stack tooling.
- 2021: "Controls Harvester", per-property text files in nested folders. It renamed controls and deleted custom keys in the stack it read, and never exported card scripts or card properties.
- 2026-11: LCHarvest2, JSON output, whole-stack and card harvesting, read-only.
- 2026-11-11: `layer` added to every control node; `tExt` renamed (compile error); rebuild library, launcher and diff tool added.


## Running it from outside LiveCode

`python/xtjson_harvest.py` (and `lcmcp harvest`, and the `xtjson_harvest` MCP tool) send a
script to LIB_MCP's `/run?in=server`. Keep in mind when changing that script:

- The file has **no `script "..."` header on purpose**: xtReemder reads it as text and it is
  pasted into stack scripts. The Python side sets it as the script of a hidden stack
  `XT_HarvestLib` and `start using`s that.
- `/run` executes through `do` inside `DevServer.Run`, which has its own locals (`tErr`,
  `tResult`). Declaring one of those again fails with "error in source expression", so the
  generated script names everything `xh...`.
- Never `exit` / `exit to top` in that script: it leaves the server's handler too and the
  client waits for a reply that never comes.
