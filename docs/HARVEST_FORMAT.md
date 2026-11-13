# Harvest format (livecode-harvest, formatVersion 2)

How to read the output of `LCHarvest2.livecodescript`. The same conventions are repeated in short form inside every `manifest.json` under `conventions`.

## Folder layout

```
harvest/<MainStackName>/
  manifest.json                 read this first
  stack_<StackName>.json        one per stack (mainstack and each substack)
  scripts/*.livecodescript      one per scripted object, byte-for-byte the original script
  assets/*                      embedded images (png, gif, jpg, bmp)
  blobs/*                       long text values (.txt) and binary custom properties (.bin)
  card_<Stack>_<id>.json        only present if a single card was harvested with harvestCard
```

All paths inside the JSON (`script.file`, `asset`, `$file`) are relative to this folder. All text files are UTF-8 with LF line endings.

## manifest.json

| Key | Meaning |
|---|---|
| `format`, `formatVersion` | `"livecode-harvest"`, `2` |
| `harvested`, `livecodeVersion`, `platform` | when and where the export ran |
| `mainStack`, `sourceFile` | name and file path of the harvested mainstack |
| `conventions` | the reading rules, as plain sentences |
| `options` | the options the exporter ran with (check `sparse` and `dedupeShared`) |
| `counts` | totals: stacks, cards, controls, scripts, files, and per type (`buttons`, `fields`, ...) |
| `stacks` | `[{name, role, file, cards, controls}]`, `role` is `main` or `substack` |
| `typeDefaults` | per object type, the properties of a freshly created object |
| `errors` | objects that failed to export; an empty list means a clean run |

Check `errors` before trusting that the harvest is complete.

## Hierarchy

```
stack
  cards[]
    controls[]            layer order, back to front
      (group) controls[]  nested children, same ordering
```

## Node keys

Every node starts with `type`, `name`, `id`. An empty `name` means the object was never named in LiveCode. Keys are omitted when they have nothing to say, except `cards` and `controls`, which are always present on stacks, cards and groups.

Stack:

| Key | Meaning |
|---|---|
| `role` | `main` or `substack` |
| `rect` | `[left, top, right, bottom]` in screen coordinates |
| `size` | `[width, height]` of the window content, which is also the card size |
| `file` | path of the stack file on the user's machine |
| `effective` | final inherited `textFont`, `textSize`, `textStyle`, `foregroundColor`, `backgroundColor` |
| `props`, `behavior`, `custom`, `script`, `cards` | see below |

Card: `number` (1-based position in the stack), `props`, `behavior`, `custom`, `script`, `controls`.

Control (`button`, `field`, `group`, `graphic`, `image`, `scrollbar`, `player`, `widget`):

| Key | Meaning |
|---|---|
| `layer` | the control's layer number on its card, 1 = backmost. A group and each of its children have their own numbers. |
| `rect` | `[left, top, right, bottom]` in card pixels, origin top-left, y down. This applies to children of groups too: rects are card-relative, not group-relative. |
| `kind` | widgets only, for example `com.livecode.widget.treeview` |
| `props` | sparse properties, see next section |
| `text` | field contents, or the menu items of a button |
| `htmlText` | fields only, present only when the field has styling beyond plain paragraphs |
| `points` | line, polygon and curve graphics: `[[x,y], ...]`, with `null` marking a break in the path |
| `asset` | images with embedded data: path of the exported image file. Images that reference a file have `fileName` in `props` instead. |
| `behavior` | LiveCode long id of the behavior object |
| `custom` | custom properties |
| `script` | script reference and handler index |
| `controls` | groups only |
| `sharedRef`, `definedOnCard` | see "Shared groups" |

## Resolving a property

`props` contains only values that differ from `typeDefaults[type]` in the manifest. To get the real value of property `p` on an object of type `t`:

1. `node.props[p]` if present (an explicit `""` means the value was cleared)
2. else `manifest.typeDefaults[t][p]` if present
3. else empty / unset

Widgets have no entry in `typeDefaults`; their `props` lists every non-empty property. If the manifest shows `options.sparse` as false, or `typeDefaults` is missing, every object's `props` lists every non-empty property and step 2 does not apply.

`typeDefaults` reflects LiveCode's template objects at harvest time, so read the actual values from the manifest instead of assuming LiveCode's documented defaults.

Geometry properties (`width`, `height`, `loc`, `left`, `top`, ...) are never in `props`. Derive them from `rect`: width = right - left, height = bottom - top.

## Value typing

- `true` / `false` are JSON booleans; plain numbers are JSON numbers.
- Comma lists of integers become arrays: colors `[r,g,b]`, `margins`, scroll values and so on.
- Text-like properties (`label`, `title`, `toolTip`, `textFont`, `fileName`, ...) are always strings, even if the text is a number.
- Colors may also be a LiveCode color name (`"red"`) or `"#RRGGBB"` string. Name-to-RGB conversion is the consumer's job.
- `icon`, `hiliteIcon` and pattern values are ids of image objects. Find the image node with that id; its `asset` or `props.fileName` gives the picture.
- Custom properties are typed more conservatively: booleans and plain numbers only. A custom value like `"1,2,3"` stays a string.

## Inheritance

A text or color property that is absent after resolving is inherited in this order: control -> enclosing group(s) -> card -> stack -> `stack.effective`. Buttons and fields with no colors of their own are drawn with the native theme in LiveCode; there is no exact RGB for that in the harvest.

## Custom properties

```json
"custom": {
  "uAction": "startGame",
  "uSpeed": 2.5,
  "uTable": {"a": 1, "b": [1, 2, 3]},
  "$sets": { "physics": {"gravity": 9.8} }
}
```

- Top-level keys are the default custom property set. `$sets` holds named sets.
- LiveCode arrays become JSON objects, or JSON arrays when their keys are exactly 1..n.
- Empty custom properties are omitted. The IDE's `cREV*` properties are omitted unless `options.ideProps` is true.
- `{"$file": "blobs/x.txt", "chars": N}` means the text is in that file.
- `{"$binary": true, "bytes": N, "$file": "blobs/x.bin"}` marks binary data.

## Scripts

```json
"script": {
  "file": "scripts/Main__button_1012_Play.livecodescript",
  "lines": 9,
  "handlers": [
    {"line": 1, "type": "on", "name": "mouseUp", "params": "pButton"},
    {"line": 6, "type": "function", "name": "nextLevel", "private": true}
  ]
}
```

- `line` is 1-based in the script file. `type` is `on`, `command`, `function`, `getprop` or `setprop`.
- Script files are named `<Stack>__<type>_<id>_<name>.livecodescript` (stack scripts: `<Stack>__stack`). The id is the stable key; names can repeat.
- When the export was made in memory (`harvestCardJSON`, `harvestControlJSON`), `file` is replaced by `text` holding the script inline.
- The handler index is a line scan, not a parser. Verify against the script file before relying on it for edits.

## Shared groups

A background group placed on several cards is written in full on the first card. On later cards it appears as:

```json
{"type": "group", "name": "NavBar", "id": 1040, "rect": [0,0,800,40], "sharedRef": true, "definedOnCard": 1002}
```

Look up the group with that `id` on the card whose `id` is `definedOnCard`. If `options.dedupeShared` is false, every card carries the full group.

## What the harvest does not contain

- Groups that are not placed on any card.
- Per-card text of fields inside a shared group, beyond the first card (when deduping).
- Native theme colors and metrics.
- Runtime state: globals, script-local variables, open/closed state of stacks.

## Query recipes

```bash
# stacks and sizes
jq '.stacks' harvest/<Main>/manifest.json

# card names of a stack
jq '[.cards[] | {number, name, id}]' harvest/<Main>/stack_<Name>.json

# every control, flattened, with its type, name, id and rect
jq '[.. | objects | select(has("rect") and .type != "stack") | {type, name, id, rect}]' harvest/<Main>/stack_<Name>.json

# every scripted object and its script file
jq '[.. | objects | select(has("script")) | {type, name, id, file: .script.file}]' harvest/<Main>/stack_<Name>.json

# where a handler is defined
grep -rn "on mouseUp" harvest/<Main>/scripts/
```


## Sampled custom data (option `customSample`, 2026-11-13)

For big stacks the harvester can sample custom property DATA instead of writing all of it
(the XTJSON Batch app does this for stacks over 2 MB, and when it retries a stack that
crashed). With `customSample` = N:
- an array value keeps its first N entries (keys sorted, numerically when they are numbers),
  nested arrays to depth 3, then `"(array of K keys)"`; plus `"$sampled": true` and
  `"$more": <entries not written>`;
- a text value longer than N lines or 2000 chars becomes
  `{"$sampled": true, "lines": L, "chars": C, "first": "<first N lines, max 1000 chars>"}`;
- a binary value becomes `{"$binary": true, "bytes": B, "$sampled": true}` (no blob file);
- a property set with more than 25 keys keeps its first N keys, with `"$sampled"` and `"$more"`.
The manifest's `options.customSample` says whether a harvest was sampled. A sampled harvest
is for understanding a stack, not for rebuilding it exactly.
