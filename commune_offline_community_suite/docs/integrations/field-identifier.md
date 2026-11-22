# Field identifier ↔ Commune drive

The Commune field identifier has five identifiers: **plants and fungi**, **animals and bugs**, **languages**, **tech** (hardware and software), and **first aid**. It uses the Commune drive as its data source, and it sends Commune everything it scanned since its last upload as one **field package**. Commune shows each package on the **Field identification** page as one upload, with its finds split into **Identified** and **Needs identification**, plus a notes box on every find.

## Folders on the drive

Everything lives in the library folder (`OfflineLibrary/` or the package's name), under `field-id/`:

```
field-id/
  inbox/        the device writes new packages here; Commune imports them on its own
  imported/     packages Commune has read (kept as a backup)
  rejected/     packages Commune couldn't read (the page lists why)
  media/<id>/   photos and sound clips from each upload
  journal.json   every upload and find, with your notes and identifications
  knowledge.json every find you identified yourself, with your source (see below)
  device.json    written by Commune for the device (see below)
```

To avoid Commune reading a half-written file, the device should write `name.zip.part` and then rename it to `name.zip`. Commune also skips files changed in the last 3 seconds.

## What the device reads: `device.json`

Commune rewrites this every time the drive is built and every time an upload is imported.

```json
{
  "communeFieldDevice": 1,
  "inbox": "field-id/inbox",
  "confidenceToIdentify": 0.8,
  "lastUpload": { "id": "fi0001-2026-11-18", "received": "2026-11-18T17:41:02-08:00", "created": "2026-11-18T17:40:00-08:00" },
  "sources": {
    "plant":     [{ "library": "gardenology_en_all", "title": "Gardenology", "file": "zim/gardenology_en_all_2025-01.zim" }],
    "fungus":    [ ... ],
    "animal":    [ ... ],
    "language":  [ ... ],
    "hardware":  [ ... ],
    "software":  [ ... ],
    "firstaid":  [ ... ]
  },
  "dictionaries": { "es": { "library": "wiktionary_es_all", "file": "zim/wiktionary_es_all_2025-03.zim" } }
}
```

- `sources` lists the ZIM files on the drive that are worth searching for each kind of find (taken from the topics in `catalog.json`).
- `dictionaries` maps a language code to its Wiktionary ZIM, if one is on the drive.
- `lastUpload.created` is the `created` time of the last package Commune received. The device can clear finds up to that time and start the next package from it.

## Your knowledge base: `knowledge.json`

When you identify a find yourself (in **Needs identification**, or after **Not right?**), you must give a source: a website, book, field guide, person, a library on the drive, or other, plus its source website (optional only for a person). The find is then marked `"identifiedBy": "user"` with a `"citation": { "type", "title", "url", "detail" }`, and Commune rewrites `field-id/knowledge.json`:

```json
{
  "communeFieldKnowledge": 1,
  "count": 1,
  "entries": [{
    "name": "Golden chanterelle", "scientific": "Cantharellus formosus", "category": "fungus",
    "identified": "2026-11-19T09:05:00-06:00", "captured": "2026-11-15T09:30:00-08:00", "location": { "label": "Under oaks near the creek" },
    "citation": { "type": "book", "title": "Mushrooms Demystified (David Arora)", "detail": "page 668", "url": "https://openlibrary.org/search?q=Mushrooms+Demystified" },
    "sources": [ ... ], "quotes": [ ... ],
    "details": { ... }, "notes": "...", "photo": "media/commune-sample/p-002-photo.png", "deviceGuess": null,
    "find": { "upload": "commune-sample", "entry": "p-002" }
  }]
}
```

**The device should search these entries along with the drive's libraries every time it scans.** Their photos (paths relative to `field-id/`) are reference pictures, and they are the person's own confirmed answers, so each identification makes the next scan better. When a match comes from here, add a source with `"kind": "knowledge"`, the find's name as `title`, and `"upload/entry"` (from `find`) as `path`: the page then links back to the earlier find. `device.json` gives the file's path and `knowledgeCount`.

On the page, a device guess that matches something you identified before is marked **You've identified this before**, with links to compare against your earlier finds.

## What the device writes: a field package

This is either a `.json` file or a `.zip` that holds `manifest.json` (the same JSON) plus the photos and clips it names. See [field-package.example.json](../field-package.example.json) for a full example.

| Field | Required | Meaning |
|---|---|---|
| `communeFieldPackage` | yes | Format version, `1` |
| `id` | recommended | Unique id for this package. Commune skips a package it has already imported, so re-sending is safe. |
| `device` | no | `{ "id", "name", "firmware" }` |
| `since`, `created` | recommended | The time span the package covers (ISO 8601 with time zone) |
| `entries` | yes | The finds (see below) |

Each entry:

| Field | Meaning |
|---|---|
| `id` | Unique within the package |
| `category` | `plant`, `fungus`, `animal` (bugs too), `language`, `hardware`, `software`, `firstaid` or `other`. `mushroom`, `bug`, `tech`, `component` and `first-aid` are also accepted. |
| `captured` | When it was scanned |
| `location` | `{ "lat", "lon", "label" }`, any of them |
| `photo`, `audio`, `translationAudio` | A path inside the `.zip` (`.jpg`, `.png`, `.webp`; `.m4a`, `.mp3`, `.wav`, `.ogg`), or a `data:` URI. 50 MB each at most. `audio` is the original speech; `translationAudio` is the voice translator's spoken translation. |
| `name`, `scientific` | What the device thinks it is |
| `confidence` | 0–1 (or 0–100) |
| `status` | Optional: `identified` or `needs-id`. If left out, a find is **identified** when it has a `name` and `confidence` ≥ 0.8. |
| `candidates` | When unsure: `[{ "name", "scientific", "confidence" }]`. The person picks one on the page, or types their own answer. |
| `quotes` | **Summaries are quotes only.** `[{ "text", "library", "title", "path", "url" }]`: text copied word for word from a library on the drive, with where it came from. `url` is the source website (see below). The device must not write its own summary. (An old-style `summary` string is still accepted, and shown as a quote with no source.) |
| `details` | The facts for its category (below). Values can be text, numbers, true/false, or lists of text. |
| `sources` | Where it looked it up: `[{ "kind", "library", "title", "path", "url" }]`. **`url` is the source website: the web page the information comes from** (for a Wikipedia article, `https://en.wikipedia.org/wiki/…`). A source can be a website with no library on the drive: give `url` and `title` only. `kind: "knowledge"` is one of your own earlier identifications (see above). `path` is the article path inside that ZIM, so the page can link straight to it. `kind` groups them on the card: `article`, `dictionary`, `image` (pictures, for the first aid dictionaries of items and injuries), `manual` (first aid manual), `video` and `lesson` (beginner videos and lessons on how to speak a language). |

### Source websites

Every source and quote has a **source website** (`url`), shown on the card as "Source: …" next to the offline link. If the device leaves `url` out, Commune works it out from the library and `path`: Wikipedia, Wiktionary, Wikibooks and Wikivoyage (`https://<lang>.wikipedia.org/wiki/<path>`), Wikispecies, Gardenology, Energypedia, MDWiki, Appropedia and iFixit, and libraries named after their site (`outdoors.stackexchange.com`, `ready.gov`, `irp.fas.org`…). Libraries with no website of their own, such as the zimgit collections, fall back to their page in the Kiwix library, so the device should send the real page for those.

The page warns when an identified find has information but no source website.

When you identify a find yourself, your source needs a **Source website** too: required for every kind of source except a person you asked. It's saved as `citation.url`.

### `details` for each category

These are the facts the page knows how to label. Anything else the device sends is still shown, under its own name. The list is `FIELD_CATS` in [web/app.js](../../web/app.js). Values can be text, numbers, true/false, lists of text, or (for `countryShare`) a map of name to value.

Every category can also send `purposes`: a list of what the find is good for, shown as **Good for** tags.

**1. Plant and fungus identifier** (`plant` or `fungus`)
A fungus is sent as `fungus` and labelled as one on the page, with the same facts as a plant. Plants and fungi share one filter.
`edibility` (edible?), `edibleAs` (spice, fruit, veggie, leaf, foliage, tree), `poisonous` (poisonous properties), `lookalikes` (dangerous look-alikes), `medicinal` (medicinal properties), `nutrition` (nutritional value), `watering` (watering recommendations), `sunlight` (sunlight type), `sunDirection`, `climate` (best climate and time of year), `fertilizers` (natural fertilizers), `pests`, `compost` (compost friendly?), `planting` (how to plant and grow abundantly), `growthTime` (expected growth time), `seeds` (how to extract seeds)

**2. Animal and bug identifier** (`animal`)
`danger` (danger level to humans), `description`, `defenses` (attack and defense mechanisms), `touch` (should you touch it?), `feed` (should you feed it?), `pestToPlants` (pest to your current plants?), `pestOf` (plants it's a pest to), `deterrents`, `attractants` (food it likes, to bring more), `edibility`, `preserveFrozen`, `preserveFridge`, `preserveOut` (if edible, how long it keeps frozen, in the fridge, and left out), `pros` and `cons` (of it being around), `cause` (why it's around), `conditions` (conditions it's found in).
`purposes`: Eating, Medicinal, Building material, Pest control, Learning, Survival, Useful resource, Clothing

**3. Language identifier** (`language`)
`language`, `languageCode` (such as `es`, for the voice and the dictionary link), `script`, `text` (word translator: what it says), `translation`, `translationLanguage` (default `en`), `pronunciation`, `historyOfText` (history behind the text), `historyOfLanguage`, `cultures` and `countries` (that speak it), `worldShare` (% of the world population who speak it), `countryShare` (% of each country who speak it, as `{ "Mexico": 98, … }`: the page lets you pick the country), `context`.
Beginner videos and lessons go in `sources` with `kind: "video"` or `"lesson"`; the dictionary link is automatic when that language's Wiktionary is on the drive. The voice translator's recordings go in `audio` and `translationAudio`; without them, the page reads the text aloud with the computer's voices.
`purposes`: Understanding, Communication

**4. Tech identifier: hardware** (`hardware`)
`whatIsIt`, `function` (what it does), `released`, `version`, `commonUses`, `specs`, `connectors`, `lifespan` (average lifespan), `components` (hardware dictionary of its components), `pairedSoftware` (commonly paired software), `softwareRequired`, `hardwareRequired` (other hardware required), `maintenance` (maintenance suggestions), `hazards` (always shown red).
`purposes`: Plumbing, Electrical, Comfort, Communications

**4. Tech identifier: software** (`software`)
`genre` (type or genre), `creator`, `released` (release date), `version`, `commonUses`, `history`, `pros`, `cons`, `hardwareRequired`, `pairedHardware` (commonly paired hardware), `subscription` (subscription required?), `security` (security recommendations), `github` (a link)

**5. First aid identifier** (`firstaid`)
`type` (item or injury), `description`, `howToApply`, `otc` (over the counter, or a medical professional required?), `naturalRemedies`, `related` (related items and injuries), `manualYear` (release year of the first aid manual it used).
Pictures for the dictionaries of items and injuries go in `sources` with `kind: "image"`, and the manual with `kind: "manual"`.
`purposes`: Mitigating further damage, Preventing ailments, Wound healing, First response, Emergency response

On the page, words like *poisonous*, *deadly*, *aggressive*, *invasive*, *hazard* or *medical professional* turn a fact's tag red, and *edible*, *safe*, *friendly*, *native* or *over the counter* turn it green. "No" to *should you touch it?* or *should you feed it?*, and "Yes" to *pest to your plants?* or *subscription required?*, are red too.
