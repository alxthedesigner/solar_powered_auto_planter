# Expand Your Knowledge and Improve Your Community
This is an offline library that gives you the hands-on skills to build a self-sufficient community that can work together for the public good. This system is built for portability and to avoid subscriptions, hidden data collection, restrictions, and full reliance on the internet.



Use Kiwix to download entire websites for self-sufficiency, building personal infrastructure outside of subscriptions, and takes in information you learn in the real world to help you solve and document problems specific to your community

## Off-Grid Library builder

Builds a plug-in survival library on an external drive. It downloads whole websites as Kiwix `.zim` files, organizes them by the topics in [offgrid_topics.txt](offgrid_topics.txt), and adds launchers so any Mac, Windows or Linux computer can browse the drive with no internet.

### Quick start

```bash
./start.command          # first run creates .venv and installs libzim, then opens http://localhost:8642
```

The app opens on a **home page** that explains what Commune is and shows your **Favorites**. **Explore Topics** goes to step 1 and **Choose Drive…** to step 2. The top bar has icon buttons for **Planter**, **Topics**, **Field ID**, **Packages** and **Queue**. The button for the page you're on, or the pop-up that's open, also shows its name; hover over the others for theirs. The steps bar (Choose topics → Choose a drive → Build & test) shows only on those three pages. Pick a drive with **Choose Drive…**, then click **Download** on a package (or **Add to queue** to combine it with other things) to start downloading it there right away. Commune starts you off with four packages of its own (Outage kit, Camping trip, Fix it yourself, Survival essentials). Click the ☆ on any package, here or under **Packages**, to choose which ones appear, and **Edit** to change one (editing an Commune package saves your own version, which you can reset). The **Field identification** box shows what your field identifier has found and opens the Field identification page (below).

To choose exactly what goes on the drive, use the three steps:

1. **Choose topics.** No drive needed yet. The pencil on each topic box renames the topic or changes which libraries it lists (**Reset to Commune's version** undoes it). Pick a category on the left and click **Add** to put libraries in your queue (the **Queue** button at the top shows what's in it). **Choose a drive** at the bottom becomes clickable once something is in the queue. Below the categories, the sidebar lists your top three packages (favorites first) with an **Add** button; **See more** opens the full Packages list. The eye button previews a library or website in a side panel before you download it, with **Visit full website** and **Copy link** for sharing; clicking an item's name opens its full website in a new tab; sites that refuse to be embedded show an **Open in new tab** button instead. **Quick add** (and **Add a website to this topic** on each card) asks you to pick a topic, then paste any website address (the eye button next to it previews the site); websites are copied with zimit (needs Docker running). The pencil button on a website edits it afterwards: a queued website can change topic and address, and one already on the drive can change topic. A library shared by several topics is downloaded once. **Save as package** keeps the queue under a name and description, so you can reuse it or share it.
2. **Choose a drive.** Pick one of two options: **Can Commune look for removable drives?** (Commune asks first, and only lists USB sticks, SD cards and external drives) or **Use a folder or another disk** (type a path and click **Use this folder**). The chosen option is highlighted and the other is greyed out; click it to switch. Each drive card says whether it's a good fit (FAT32's 4 GB limit, low space). "How much space do you need?" compares the drive with the Essentials, your two latest packages, and everything. **Download & continue** starts the downloads into one folder on the drive: `OfflineLibrary/`, or the package's name when you download a package. If the drive already has a library, Commune keeps using that folder.
3. **Build & test the drive.** Watch downloads finish, tick which computers should open the drive, then click **Build drive** (it adds the reader apps too). The app tells you when something new needs another build. **Start reader** lets you test it.

Next time you open the app, it asks before reconnecting to your drive. Choose **Connect, and don't ask again** to skip that (and **Yes, and don't ask again** to skip the drive-scan question); **Ask me again** on step 2 turns both prompts back on.

**Packages** (the box icon in the top bar) lists every package, with search. **Add to queue** loads one, **Edit** changes its name, description and contents, **Export** saves it as a `.commune-package.json` you can send to someone, and **Import a package** loads one you were given. Packages are kept in `packages.json` next to the app.

### Field identification

The **Field ID** button in the top bar opens the finds from the Commune field identifier, a handheld scanner with five identifiers: plants and fungi, animals and bugs, languages, tech (hardware and software), and first aid. The device looks things up in the drive's libraries and saves everything it scanned since its last upload as one package in the drive's `field-id/inbox/` folder. Commune imports it automatically, or you can use **Import upload** to pick the file yourself.

- Each upload is listed on the left (**Latest** at the top). Finds are split into **Identified** and **Needs identification**, which holds anything the device was less than 80% sure about. Filter by plants and fungi, animals and bugs, languages, hardware, software or first aid.
- Each find shows what you can do with it, and **Good for** tags for its uses (eating, clothing, pest control, wound healing, plumbing…). For example: how to water, plant and harvest seeds from a plant, and its dangerous look-alikes (mushrooms are labelled as fungi); whether an animal is dangerous, a pest to your plants, safe to touch or feed, and how long it keeps if you eat it; what a piece of hardware or software needs, its hazards, and how to maintain or secure it; how to apply a first-aid item, and whether it needs a medical professional. Danger words make a tag red, and safe ones make it green.
- **Summaries are quotes only.** Each one is copied word for word from a library on the drive, with a link to where it came from.
- Every source and quote shows its **source website**: the web page the information comes from. Commune works it out from the library when the device doesn't send it.
- Language finds show the text, its translation and pronunciation, history, and who speaks it worldwide and in a country you pick. **Hear it** buttons use the device's recordings, or the computer's built-in voices. They link to the Wiktionary for that language if it's on the drive (start the reader in step 3 first), or offer to add it to your queue, plus any beginner videos and lessons.
- Finds show as condensed cards (photo, name, how sure the device was, two key facts). Click one to open everything about it, and **Show less** to fold it back.
- The search bar searches every find: names, uses, facts, quotes, places, your sources and your notes.
- To identify a find yourself, pick one of the device's guesses or type your own answer, then add **your source** (a website, book, field guide, person, or a library on the drive) and its **source website**. Both are required, except that a person you asked needs no website. The find moves to Identified, marked **Identified by you** with its source. **Not right?** moves it back.
- Everything you identify yourself goes into your knowledge base, `field-id/knowledge.json`. The field identifier searches it every time it scans, so your knowledge grows with every find. When the device's guess matches something you identified before, the card says so and links to your earlier find.
- Every find has a **Your notes** box, which saves as you type.

Finds, photos and notes are kept on the drive in `field-id/`. With no drive connected, they're kept next to the app in `field-id/` instead. The first time the page opens, it loads **Sample finds (Commune)**, one test find for each kind (delete them with **Delete upload**, or bring them back with **Load sample finds**). `field-id/device.json` tells the device which libraries and dictionaries are on the drive and when its last upload arrived. The package format is in [docs/integrations/field-identifier.md](docs/integrations/field-identifier.md), with an example at [docs/field-package.example.json](docs/field-package.example.json).

### Planter

The **Planter** button in the top bar opens readings from the automated planter: soil moisture for each zone, the rain tank, battery and solar, and temperature. It also shows a moisture chart (24 hours, 7 days or 30 days) and the planter's recent activity. The page uses the landing page's green colours. It shows the zones and rain drums the planter reports it has (up to 8 zones and 4 drums), and you can name them. Under **Watering settings** you choose the watering hours and the lowest battery it may water on. For each zone you choose **when to water** (when the soil is dry, or on a schedule every N days), how much, and the most per day. **Growing here** links plants you identified on the Field identification page to a zone.

Planter data is kept on this computer, in `planter/` next to the app, not on the drive. Under **How the planter reaches Commune**:
- **Wi-Fi bridge:** enter the Raspberry Pi's address and key. Commune collects new readings every 2 minutes while it's open, and sends your settings.
- **SD card:** plug in the planter's card, then **Import readings** or **Write settings to card**.
- **Phone page:** settings changed on the planter's own hotspot page show up as a notice, with **Keep the planter's settings** or **Send Commune's settings to it**.

The format is in [docs/integrations/planter.md](docs/integrations/planter.md). The planter itself is in `automated_planter_system/` next to this folder.

Off-grid: plug in the drive and double-click `START-Mac.command` or `START-Windows.bat`, or run `sh START-Linux.sh`. The browser opens the Off-Grid Field Guide.

### Where content comes from

| Source | What it is |
|---|---|
| **Kiwix catalog** | 46 real ZIMs mapped to topics in [catalog.json](catalog.json): WikiMed, Military Medicine, zimgit Water/Food/Knots/Post-Disaster, Wiktionary (EN/ES/FR/ZH), Wikipedia EN/ES, iFixit, Ham Radio Q&A, Outdoors Q&A, Gardenology, Ready.gov, and others. Sizes and download URLs are fetched live from `library.kiwix.org`, so you always get the newest version. |
| **Off-Grid Field Guide** | A pseudosite generated by [build_guide.py](build_guide.py) from [guide_content.py](guide_content.py), with one quick-reference page per topic. It is the drive's home page and links into every library on the drive. It covers topics that have no dedicated ZIM, such as tracking, smoking food, traps, and predator defence. |
| **zimit crawls** | Any website you choose, crawled in Docker (`ghcr.io/openzim/zimit`) and tagged to a topic. |

Some libraries come in several **flavours**: `maxi` (full), `nopic` (no images), and `mini` (intros only). Each row has a picker. Large ones default to `nopic`.

Downloading every library at the default flavours needs about **127 GB**, and full English Wikipedia alone is 49 GB. The essentials (medicine, water, food, knots, outdoors, radio, mechanics) fit in under 10 GB.

### Drive layout

```
OfflineLibrary/             (or your package's name)
  zim/                      all .zim files (offgrid-field-guide.zim is the home page)
  kiwix-tools/<platform>/   kiwix-serve for each OS you installed
  library.xml               Kiwix index of zim/
  START-Mac.command  START-Windows.bat  START-Linux.sh
  README-FIRST.txt
  custom.json               websites you crawled
  field-id/                 field identifier uploads, photos, your notes, and device.json
```

Phones and tablets can open the `.zim` files directly with the free Kiwix app.

### Notes

- **Format the drive as exFAT** (or APFS/NTFS/ext4). FAT32 can't hold files over 4 GB; the app warns you and blocks those downloads.
- Downloads resume if interrupted: queue the same library again.
- Crawls copy the ZIM out of the container with `docker cp`, so Docker file-sharing settings don't matter. Only crawl sites you're allowed to copy, and set a page limit.
- Edit [catalog.json](catalog.json) to add topics or map more Kiwix libraries. Library names come from https://library.kiwix.org.
- The field-guide pages are short references, not a substitute for first-aid or firearms training.
