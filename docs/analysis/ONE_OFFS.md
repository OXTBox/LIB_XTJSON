# The rest of the 2026-11-13 batch: one-off stacks, what each is and what to reuse

Saturday, November 14, 2026. Claude (Opus 5.5), LIB_SYSTEM TODO A-12, the part after Generica
(`LIB_GAD/GENERICA_TEMPLATE.md`) and CLIP / DND / TTRPG / Enochian (`CLIP_DND_ENOCHIAN.md`).
Source: every harvest under `~/projects/XTJSON/batch/` not covered there, about 70 stacks. Each
was read through `tools/harvest_summary.py` (handlers, sizes, custom properties, field text) and
the header comments of its biggest script. Verdicts come from that reading, not from running the
stacks. `Web_Collector_Watcher` and `CollectorStacks` have no `manifest.json` (an older harvest),
so their stack files were read directly.

Verdicts: **keep** (bring into a LIB), **adapt** (take the idea or a helper), **personal** (a
working tool of the owner's; leave it alone), **reference** (someone else's code; read it, don't
copy it in), **drop**.

## The owner's own stacks

| Stack (newest) | What it is | Size | Verdict | Goes to |
|---|---|---|---|---|
| `Stick_Figure_Bubble_Man` | **a BVH player in plain LiveCode**: parses the hierarchy and motion, works out joint world positions from Euler rotations, projects 3D to 2D (front view) and moves oval joints; started from the skytopia "3D cube in 2D" tutorial, plus cylinder / sphere / cone | 2,778 lines, 84 handlers | **keep** | LIB_MOCAP / LIB_BVH: the LiveCode side of the BVH library (the Python side is `mocap_lib.py`); compare its joint maths with `wif.py` |
| `BitFontMaker_02_20_2026` | a bitmap font editor: grid drawing, frames, undo, shifting pixels, binary strings per row, a font viewer and a "Dissect" stack | 7 stacks, 3,730 lines, 209 handlers | **keep** | LIB_BIT (1-bit fonts); the Python reader is already in the inbox (`LIB_LLMIN/LIB_DEE/BitFontMaker2_Reader_Python`) |
| `GAD_Globals` | **the owner's first globals register**: 165 globals as a property set, each with a comment, then turned into `comment / owner / type / content` records (b... names → Boolean) | 231 lines, 27 handlers | **keep** | LIB_GLOBALS: the census already uses its comments as purposes; its record shape (`owner`, `type`, `content`) is the one to add to `globals.json` |
| `GAD_SendTo_And_Zoom_NODES` | a node map: nodes as graphics, "send to" paths between them, rendezvous, zoom, the centre of the map | 585 lines, 37 handlers, 162 controls | adapt | GAD's star map (the Galactica fleet "send to" orders); LIB_MAP |
| `GAD_Inspector`, `InspectorType`, `Game_Object_Properties_Manager` | forms over the GAD data (an attributes table; `InspectorType` has no scripts; the manager is 96 controls with one `sortClipboard` handler) | small | adapt | one Generica/GAD inspector (with the iGame3D Inspector, `LIB_ig3d/MAIN_UI_REUSE.md`) |
| `Collect_stacks_export_everything` | "Derived from iGame3D_UI_Main Stack 2007": file handling, backup folders, save data to file, folder lists | 2,017 lines, 92 handlers | reference | LIB_XTJSON's harvester does this job now; keep for its backup-folder helpers |
| `CollectorStacks/Collector_v11022026` | a collector app: finds PNGs and files, pulls images out of JSON, **builds popup buttons and their scripts at run time** | 2,780 lines, 104 handlers | adapt | the folder walker (pattern 3 in `CLIP_DND_ENOCHIAN.md`); the script-writing buttons go with `GAD_SELF_WRITING_SCRIPTS.md` |
| `Web_Collector_Watcher` | watches a browser cache folder, keeps favourites, **tells a file's type from its first bytes** (hex magic numbers) | 1,270 lines, 114 handlers | personal; take one helper | `GetFileType` / `ConvertHexToBinary` as a small LIB_XTJSON helper (a file with the wrong extension) |
| `Schema_Livecode_thing` (stack `LOVELY_HTML_OF_STACK`) | JSON → JSON Schema, and JSON made safe for LiveCode arrays (numeric keys as lists, enums) | 364 lines, 17 handlers | **keep** | LIB_XTJSON: a schema for every harvest file, and for GAD data |
| `Read_SRT_Stack2` | reads `.srt` subtitles into a timeline of lines with a cast list and locations per scene, exports all | 3 stacks, 432 lines, 33 handlers | adapt | the Sequencer (`.seq`): timed lines for talking scenes in PROMPT & GLAZE |
| `CO_DemoReader_Main` / `Demolisher_0005a_Current` | a 2013 reader and player for a game's `.demo` recordings (entities, raw data, render scale, time step); the About card has its version history | 5 stacks, 631 lines, 53 handlers | reference | its recursive file-listing helpers (`listFilesWithPaths` ...) are textbook; the rest belongs to that game |
| `ImageOrganizer_03222025b` | sort images into folders by key, preview, undo the last move | 762 lines, 49 handlers | personal | - |
| `MusicLoader` | a music list with players: cycle, random, view current song | 339 lines, 24 handlers | adapt | game background music (one helper for every Vibecode3D game) |
| `Hexes_but_bad_Offsets` | draws hex tiles and seamless hex tile images ("bad offsets" by its own name) | 404 lines, 14 handlers | adapt | LIB_MAP hex grids; find the offset fault before reuse (not traced here) |
| `Adventurer_sprite` | a sprite sheet cut into tiles, set the sprite to a frame | 77 lines, 7 handlers | adapt | LIB_BIT sprites / a 2D frame player |
| `Bezier.livecode` | Bézier handles: anchors and controls dragged, angle ↔ loc | 155 lines, 13 handlers | adapt | a curve tool for the editors (paths, the old iGame3D path mode) |
| `LemniskateBN_7` | a point moving on a figure-8 (lemniscate) with a fading trail | 353 lines, 13 handlers | adapt | a motion-path example for LIB_HOWTO |
| `BATCH_Livecode` (BatchArtPrompter, Batch_Renamed_Collected, TextItemizer, ScrapController) | small text tools: prompt batches, renaming, itemising pasted text | 15-98 lines each | adapt | pattern 4 (words → prompt) with the Spark tools |
| `SuspectIPProcKillerv02` | lists processes and their network addresses against a threats list (data grid), closes them | 3 stacks, 376 lines | personal | - (a system tool, not game work) |
| `Fallout4_Livecode` (Drop/Equip Items Manager, FO4Locations) | console-command builders for Fallout 4 | 51-234 lines | personal | - |
| `1bit_to_3D_utility_Prototype` | 9 controls, no scripts | - | drop | replaced by the BitEditor (LIB_BIT) |
| `DynamicBlur`, `camouflage`, `Resize a rect in any direction` | small UI tricks (blur slider, screen-capture camouflage, rect resize) | 11-108 lines | drop (reference) | - |
| `Status_Browser` | the review dashboard's layout (LLM note, feedback, list) | no scripts in the harvest | - | it is LIB_DEV's own stack; harvested by mistake or as a backup |

## Other people's stacks (reference only: read them, don't fold them into our LIBs)

| Stack | Author per its own text | Licence seen | What to learn |
|---|---|---|---|
| `arcade_engine_6demo` (`animationEngine`, `ae6demo`, `collisionListenerDemo`) and `map_zoom` (uses it) | Malte Pfaff-Brill (animationEngine) | GPL (stated in the script) | collision callbacks, constrained dragging, eased moves. GPL: copying it in would make that LIB GPL |
| `Invaders/Invaders` | John Craig, 2013 (splash21.com) | GPL (stated) | a complete small arcade game in one card: 603 controls, a 605-line loop; a good size target for our demos |
| `Invaders/getinline` | not stated in the header | - | drag-to-reorder list lines |
| `bouncy` (+ `video_capture`) | not stated in the header | - | drag-drop images that bounce; video capture |
| `Scott_Rossi_Stacks_Perhaps_question_mark` (26 stacks: Calendar, DateTime, XMLdemo, POP/SMTP libraries, MySQL, StackDock, RevGZ, UnixCal, PlistEditor...) | Revolution-era freeware; the scripts' own credits name "Sarah" in most and Scott Rossi / "troz" in some, so the folder holds more than one author | per stack | `DateTime` (1,057 lines of date maths), `Colors` (RGB ↔ HSV), `XMLdemo` (XML tree). Their mail / MySQL / serial / Mac plist code is out of date |

## What this adds to the proposals

- **P4** Bring `Stick_Figure_Bubble_Man`'s BVH code into LIB_MOCAP as the LiveCode reader, so a
  Vibecode3D game can play a BVH clip without Python. Cost: medium (2,778 lines; the BVH part is
  about a third).
- **P5** Add `owner / type / content` from `GAD_Globals` to the LIB_GLOBALS register. Cost: small.
- **P6** `Schema_Livecode_thing` → a schema per XTJSON file type. Cost: small.
- Licence note for the owner: animationEngine and Invaders are GPL. They're fine as reference,
  but code copied from them into a LIB that goes public (LIB_PUBLIC, itch.io) would carry the GPL.
