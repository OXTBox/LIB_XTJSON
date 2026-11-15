# CLIP, DND / TTRPG and Enochian: what the newest stacks are and what to reuse

Saturday, November 14, 2026. Claude (Opus 5.5), LIB_SYSTEM TODO A-12 (the part after
Generica, which is `LIB_GAD/GENERICA_TEMPLATE.md`). Source: the 2026-11-13 XTJSON batch,
newest builds per `~/projects/XTJSON/batch/_NEWEST.md`, read through the new
`LIB_XTJSON/tools/harvest_summary.py` (a short summary per harvest instead of the raw JSON).
Content of the owner's personal collections (image captions, clip names) is described, not quoted.

## In one table

| Family | Newest stack | What it really is | Size | Keep for |
|---|---|---|---|---|
| CLIP | `CLIP_List_09_08_2025` | a media-folder browser: collects PNGs, texts and stacks from a folder, shows them, plays through them, stores images inside custom properties, makes a prompt from the selection | 1,023-line stack script, 62 handlers | the folder watcher and the image-in-a-property helpers |
| CLIP | `CLIP_Interrogation_compiler_empty2` | a caption ("interrogation") collector: walks category folders, pairs each image id with its caption text, renames, de-duplicates, saves into the stack | 179 lines, 10 handlers; data in custom prop `CLIPs` | the category-folder walk + rename/dedupe pattern |
| CLIP | `CLIP_DB` | data only: the `CLIPs` array (about 8 kB), no controls | - | nothing new (a saved copy of the compiler's data) |
| TTRPG | `TTRPG_STUDIO_020920229AM` | **a tabletop game engine with an LLM narrator**: actors, items, containers, locations, a world map; turns built as a packet and sent to a local LM Studio model | 1,595-line stack script (79 handlers) + 606-line card script | the most reusable stack in this group (see below) |
| TTRPG | `That_DND_LLM_WORLD_BUILDER_THING` | the earlier build of the same studio (`lmstudioapilib_0202026`) | 1,312 + 561 lines, 65 handlers | superseded by TTRPG_STUDIO |
| DND | `Imported_DND_Lists_VERSION_002` | a CSV/TSV importer: D&D equipment sheets (name, type, properties, D&D Beyond link) into fields and a `merchandise` property set | 151 lines, 7 handlers; 76 fields | the CSV → property-set import |
| DND | `DND_Inventory_2` | the same importer grown into an item editor that exports each item as JSON (`BuildItemJSON`, `ExportMerchandiseToJSON`) | 217 lines, 10 handlers | item → JSON export |
| DND | `LOAD_DND_JSON_worksButDoesIt` | a three-level JSON browser (category → entry → attribute) over D&D class/species/spell/weapon files | 4 field scripts | the drill-down list pattern |
| Enochian | `Enochian_07_07_2025` | an interactive **Great Table** (watchtowers): 675 clickable cell graphics, sigils traced as coordinate sequences, history/undo, governor enumeration, sigil image export | 966 lines, 58 handlers; 11 data sets | the clickable-grid + traced-path + export tools |
| Enochian | `Enochian_Angels` | angel names → descriptions → an image-generation prompt with weights (`[female:male:0.33]`) | 115 lines, 5 handlers | the words → weighted-prompt builder |
| Enochian | `enochian_gemetria` | a gematria calculator over an Enochian dictionary (word → number) | 3 button scripts + 1 field script | small; a lookup example |
| Enochian | `VisionAndTheVoice` | the 30 aethyrs: list, vision text, pronunciation | 44 lines, 3 handlers | data |

## TTRPG Studio, the one to build on

It is already most of a game back end, written in the same style as GAD (property sets as the
database, `init.*` / `string.*` / `UI.*` handler prefixes):

| Part | Handlers (examples) | Where it fits now |
|---|---|---|
| World data | `World` set (`current_world`, `Example_01_World`), `world.array`, `world.location.array.by.name`, `init.RandomMapGenerator` | a cellmap v2 map can be the world's layout; locations = cellmap `[objects]` |
| Things | `BuildActor`, `AddItemToActor`, `MoveItemBetweenContainers`, `generate.container.and.AdventureGear`, `nouns` set (class, containers, ecosystem, locations, monsters, npc, species), 62 `roles` | LIB_GENERICA's word sets (same idea, one format) |
| Save / load | `SaveActorToJSON`, `LoadLocationFromJSON`, `SaveAllWorldObjectsToJSON` | fine as is; JSON per object |
| Turns | `initTurn`, `BuildTurnPacket`, `GetVisibleRoomStateForPlayer`, `BuildPlayerTurnPrompt`, `InterpregPlayerAction` | the loop a PROMPT & GLAZE conversation scene needs |
| LLM | `LM_Init`, `LM_TestConnection`, `LM_BuildRequestJSON`, `LLM_system_prompts` set (`describe_a_tile`, `ttrpg_personas`), `lm_url` / `lm_model` | the local model (LM Studio). Same role Spark plays for us |

Faults seen in passing (not fixed; the harvest is read-only): handler names repeated
(`SaveWorldObjectToJSON` twice, `show.history` twice in Enochian, `init.globals` twice) — the
later one wins in LiveCode, so the first is dead code; field names repeated many times on one
card (`WeaponField1` x4, `CharacterClassField1..4` copied in two groups), so `field "WeaponField1"`
always finds the first; a handler called `wtf`; `InterpregPlayerAction` (typo, but callers match).

## Patterns that repeat across all three families (worth one library each)

1. **A property set as the database**, a list field to pick a key, fields to edit its values
   (DND, TTRPG, Enochian, Generica). → LIB_GENERICA already is this; the others can load into it.
2. **Import a sheet (CSV/TSV/JSON) into property sets**, export one entry as JSON
   (DND_Inventory_2, TTRPG). → one importer in LIB_GENERICA `tools/`.
3. **A folder walker that pairs files with their text and stores them in the stack**
   (CLIP compiler, CLIP_List). → LIB_XTJSON already walks folders; reuse its walker.
4. **Words → a weighted prompt** (Enochian_Angels, TTRPG system prompts, CLIP `getPrompt`).
   → a small prompt builder next to the Spark tools.
5. **A big clickable grid of graphics with traced paths** (Enochian Great Table, 675 cells).
   → the BitEditor / cellmap grid does this now, faster (one image instead of 675 graphics).

## Proposals (owner decides)

- **P1** Make TTRPG Studio's data and turn loop the back end of a PROMPT & GLAZE talking scene:
  GLAZE's barter/charm/influence as LLM-judged actions. Cost: medium; first a read of its
  1,595 lines by an AI with the full script open.
- **P2** One importer (pattern 2) into LIB_GENERICA, then load the D&D equipment lists and the
  TTRPG `nouns` / `roles` sets as Generica themes. Cost: small.
- **P3** Leave CLIP and Enochian as they are (personal tools that work); take only the helpers
  named in the table when another stack needs them.
