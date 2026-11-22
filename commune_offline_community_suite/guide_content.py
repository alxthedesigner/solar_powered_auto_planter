"""Pages for the built-in "Off-Grid Field Guide" pseudosite.

Each entry is the HTML body for one topic id in catalog.json. These are short
field references so every topic has *something* on the drive even before the
large Kiwix libraries finish downloading. They are not a substitute for
training; the linked libraries go much deeper.
"""

WARN = '<p class="warn">{}</p>'

PAGES = {
# ---------------------------------------------------------------- wildlife
"plant-id": """
<p>Identify a plant from <b>several</b> features, never one. Write them down before you consult a reference.</p>
<h2>What to record</h2>
<ul>
<li><b>Leaf arrangement</b>: alternate, opposite, whorled, or basal rosette.</li>
<li><b>Leaf type</b>: simple or compound (leaflets on one stalk). Note edges: smooth, toothed, lobed.</li>
<li><b>Stem</b>: round, square (mint family), hollow, hairy, milky sap.</li>
<li><b>Flowers</b>: petal count, colour, symmetry, cluster shape (umbrella-shaped clusters = carrot family, which includes deadly hemlock).</li>
<li><b>Smell</b> of a crushed leaf, <b>habitat</b>, and <b>season</b>.</li>
</ul>
<h2>Families worth learning first</h2>
<table><tr><th>Family</th><th>Tell</th><th>Notes</th></tr>
<tr><td>Mint (Lamiaceae)</td><td>Square stem, opposite leaves, aromatic</td><td>Almost all are safe; good teas.</td></tr>
<tr><td>Mustard (Brassicaceae)</td><td>4 petals in a cross, 6 stamens (4 tall, 2 short)</td><td>Generally edible, peppery.</td></tr>
<tr><td>Grass (Poaceae)</td><td>Hollow jointed stems</td><td>Seeds edible; discard any with purple/black ergot fungus.</td></tr>
<tr><td>Carrot (Apiaceae)</td><td>Umbrella flower clusters</td><td><b>Avoid unless expert</b>: water hemlock and poison hemlock kill.</td></tr>
<tr><td>Nightshade (Solanaceae)</td><td>5 fused petals, star shape</td><td>Many are toxic; avoid wild ones.</td></tr></table>
<h2>Universal edibility test: last resort only</h2>
<p>Test one part of one plant, fasting 8 hours first: smell it; rub on inner wrist for 15 minutes; touch to lip 3 min; hold on tongue 15 min; chew without swallowing 15 min; swallow a teaspoon and wait 8 hours. Any burning, numbness, itching or nausea = reject. <b>This test does not work for mushrooms</b> and will not catch slow-acting toxins.</p>
""" + WARN.format("Never eat wild mushrooms unless an experienced local forager confirms the species in person. Deadly Amanitas taste fine and symptoms start after liver damage has begun."),

"animal-id": """
<h2>Observe in this order</h2>
<ol><li>Size relative to something known (house cat, dog, deer).</li>
<li>Shape and posture: how it moves (bounds, waddles, walks).</li>
<li>Colour pattern and distinctive marks: tail rings, white rump, facial stripes.</li>
<li>Sound, time of day it is active, and habitat.</li></ol>
<h2>Dangerous animals by region (North America)</h2>
<table><tr><th>Animal</th><th>Key ID</th><th>Response</th></tr>
<tr><td>Black bear</td><td>No shoulder hump, tall pointed ears, straight face profile</td><td>Stand tall, be loud. Fight back if attacked.</td></tr>
<tr><td>Grizzly/brown bear</td><td>Shoulder hump, dished face, short round ears</td><td>Bear spray; if contact, play dead face-down.</td></tr>
<tr><td>Mountain lion</td><td>Long thick tail, tan, ~1.5–2.5 m with tail</td><td>Never run; look big, fight back.</td></tr>
<tr><td>Rattlesnake</td><td>Triangular head, rattle, heat pits</td><td>Back away slowly; 1.5 m+ clearance.</td></tr>
<tr><td>Coral snake</td><td>Red touches yellow (US only rule)</td><td>Do not handle any banded snake.</td></tr></table>
<p>See also <a href="tracking.html">Animal tracking</a> and <a href="predators.html">Predator defence</a>.</p>
""",

"poison": """
<h2>Signs of poisoning</h2>
<p>Burns or stains around the mouth, vomiting, confusion, drowsiness, seizures, trouble breathing, abnormal pupils, chemical smell on breath.</p>
<h2>First steps</h2>
<ol><li>Make the scene safe; remove the person from fumes into fresh air.</li>
<li>Remove contaminated clothing; flush skin with running water for 15–20 minutes. Flush eyes for 15 minutes.</li>
<li><b>Do not induce vomiting</b> unless poison-control or a medic tells you to. Corrosives burn twice.</li>
<li>If unresponsive and not breathing normally, start <a href="cpr.html">CPR</a>. Place breathing but unconscious casualties in the recovery position.</li>
<li>Keep the container, plant, or a photo of the substance with the casualty.</li></ol>
<h2>Common wilderness poisons</h2>
<table><tr><th>Source</th><th>Notes</th></tr>
<tr><td>Water/poison hemlock</td><td>Seizures within minutes to hours. Carrot-family look-alikes.</td></tr>
<tr><td>Death cap / destroying angel</td><td>Symptoms delayed 6–24 h, then liver failure.</td></tr>
<tr><td>Foxglove, oleander, lily-of-the-valley</td><td>Heart rhythm problems.</td></tr>
<tr><td>Carbon monoxide</td><td>Headache, dizziness. Never run stoves/generators in a closed shelter or bunker.</td></tr>
<tr><td>Snake bite</td><td>Keep limb still at heart level, remove rings, no tourniquet, no cutting/sucking. Evacuate.</td></tr></table>
""",

"climate": """
<h2>Read the sky</h2>
<table><tr><th>Sign</th><th>Usually means</th></tr>
<tr><td>Cirrus "mares' tails" thickening to sheet cloud</td><td>Warm front, rain within 12–24 h</td></tr>
<tr><td>Towering cumulonimbus, anvil top</td><td>Thunderstorm, hail, lightning soon</td></tr>
<tr><td>Halo around sun/moon</td><td>Moisture aloft, rain likely in a day</td></tr>
<tr><td>Falling barometer &gt; 1 hPa/hour</td><td>Storm approaching</td></tr>
<tr><td>Morning dew/fog in valleys</td><td>Usually a fair day</td></tr></table>
<h2>Climate zones at a glance</h2>
<ul><li><b>Desert</b>: travel at dawn/dusk, cover skin, ration sweat, not water.</li>
<li><b>Temperate</b>: four seasons. Plan food storage for winter.</li>
<li><b>Tropical</b>: rain daily; elevate sleeping, treat all water.</li>
<li><b>Boreal/Arctic</b>: insulation and dry clothing beat everything; "cotton kills".</li>
<li><b>Mountain</b>: about 6.5 °C cooler per 1000 m climbed; weather turns fast.</li></ul>
<h2>Lightning</h2>
<p>30/30 rule: if thunder follows the flash within 30 s, shelter; wait 30 min after the last thunder. Avoid peaks, lone trees and water. Crouch on a pack with feet together if caught in the open.</p>
""",

"tracking": """
<h2>Reading a track</h2>
<ul><li><b>Count toes</b>: 4 front/4 hind with claws (dog family); 4/4 without claws (cat family; claws retract); 5/5 (bear, raccoon, weasels); 4 front/5 hind (rodents).</li>
<li><b>Hooves</b>: two-toed slots = deer, elk, pigs, goats. Dewclaw marks show the animal was running or in soft ground.</li>
<li><b>Shape</b>: canine tracks are oval with an X-shaped negative space; feline tracks are round with a three-lobed heel pad.</li></ul>
<h2>Gait patterns</h2>
<table><tr><th>Pattern</th><th>Animals</th></tr>
<tr><td>Diagonal walk (zig-zag pairs)</td><td>Deer, dogs, cats, foxes (foxes very straight)</td></tr>
<tr><td>Pace (both left, then both right)</td><td>Bears, raccoons, beavers, porcupines</td></tr>
<tr><td>Bound (pairs side by side)</td><td>Weasels, otters, mink</td></tr>
<tr><td>Gallop (groups of 4, hind feet in front)</td><td>Rabbits, squirrels, mice</td></tr></table>
<h2>Aging sign</h2>
<p>Crisp edges and no debris = fresh. Rain, leaves or insect trails inside the print = older. Fresh scat is moist and shiny. Snap twigs and watch how quickly they discolour to calibrate.</p>
<p>Follow game trails to water at dawn and dusk; look for rubs, beds, chewed bark and droppings.</p>
""",

"spice-plants": """
<p>Wild and garden plants that add flavour, preserve food, or both. Confirm ID before using (see <a href="plant-id.html">Plant identification</a>).</p>
<table><tr><th>Plant</th><th>Part</th><th>Flavour / use</th></tr>
<tr><td>Wild garlic / ramps</td><td>Leaves, bulb</td><td>Garlic-onion. Must smell of garlic; lily-of-the-valley look-alike does not.</td></tr>
<tr><td>Wild mint</td><td>Leaves</td><td>Tea, meat, digestion</td></tr>
<tr><td>Juniper</td><td>Ripe blue berries</td><td>Pine-pepper for game meat. Use sparingly; avoid in pregnancy.</td></tr>
<tr><td>Spicebush</td><td>Berries, twigs</td><td>Allspice substitute (eastern N. America)</td></tr>
<tr><td>Garlic mustard</td><td>Leaves, seeds</td><td>Garlic + mustard heat</td></tr>
<tr><td>Wild ginger (Asarum)</td><td>Root</td><td>Ginger-like. Small amounts only (contains aristolochic acid).</td></tr>
<tr><td>Sumac (red, upright clusters)</td><td>Berries</td><td>Lemony; soak for "sumac-ade". White-berried poison sumac is different.</td></tr>
<tr><td>Wild fennel, dill</td><td>Seeds</td><td>Anise flavour. Carrot family: <b>expert ID only</b>.</td></tr>
<tr><td>Sweetfern, bay laurel</td><td>Leaves</td><td>Bay substitute for stews</td></tr>
<tr><td>Salt</td><td>Seawater</td><td>Boil or sun-evaporate seawater: about 35 g salt per litre.</td></tr></table>
<p>Grow your own: thyme, oregano, sage, rosemary, chives and coriander tolerate poor soil and dry easily.</p>
""",

# ---------------------------------------------------------------- language
"dict-es": """
<p>The full English↔Spanish dictionary lives in the <b>Wiktionary</b> libraries below: search an English word and scroll to <i>Translations</i>. Quick list:</p>
<table><tr><th>English</th><th>Spanish</th></tr>
<tr><td>water / food</td><td>agua / comida</td></tr><tr><td>help!</td><td>¡ayuda!</td></tr>
<tr><td>doctor / hospital</td><td>médico / hospital</td></tr><tr><td>danger</td><td>peligro</td></tr>
<tr><td>fire</td><td>fuego</td></tr><tr><td>where is…?</td><td>¿dónde está…?</td></tr>
<tr><td>I am hurt</td><td>estoy herido/a</td></tr><tr><td>I need…</td><td>necesito…</td></tr>
<tr><td>left / right / straight</td><td>izquierda / derecha / recto</td></tr><tr><td>north / south / east / west</td><td>norte / sur / este / oeste</td></tr>
<tr><td>yes / no / please / thank you</td><td>sí / no / por favor / gracias</td></tr></table>
""",

"dict-zh": """
<p>Use <b>Chinese Wiktionary</b> or the English Wiktionary <i>Translations</i> section for full entries. Pinyin tones: ā (high) á (rising) ǎ (dip) à (falling).</p>
<table><tr><th>English</th><th>Mandarin</th><th>Pinyin</th></tr>
<tr><td>water</td><td>水</td><td>shuǐ</td></tr><tr><td>food</td><td>食物</td><td>shíwù</td></tr>
<tr><td>help!</td><td>救命！</td><td>jiùmìng!</td></tr><tr><td>doctor</td><td>医生</td><td>yīshēng</td></tr>
<tr><td>hospital</td><td>医院</td><td>yīyuàn</td></tr><tr><td>danger</td><td>危险</td><td>wēixiǎn</td></tr>
<tr><td>fire</td><td>火</td><td>huǒ</td></tr><tr><td>where is…?</td><td>…在哪里？</td><td>…zài nǎlǐ?</td></tr>
<tr><td>I am hurt</td><td>我受伤了</td><td>wǒ shòushāng le</td></tr><tr><td>I need…</td><td>我需要…</td><td>wǒ xūyào…</td></tr>
<tr><td>yes / no</td><td>是 / 不是</td><td>shì / bú shì</td></tr><tr><td>thank you</td><td>谢谢</td><td>xièxie</td></tr></table>
""",

"dict-fr": """
<p>Full entries are in <b>Wiktionnaire</b> and English Wiktionary. Quick list:</p>
<table><tr><th>English</th><th>French</th></tr>
<tr><td>water / food</td><td>eau / nourriture</td></tr><tr><td>help!</td><td>au secours !</td></tr>
<tr><td>doctor / hospital</td><td>médecin / hôpital</td></tr><tr><td>danger</td><td>danger</td></tr>
<tr><td>fire</td><td>feu</td></tr><tr><td>where is…?</td><td>où est… ?</td></tr>
<tr><td>I am hurt</td><td>je suis blessé(e)</td></tr><tr><td>I need…</td><td>j'ai besoin de…</td></tr>
<tr><td>left / right / straight</td><td>gauche / droite / tout droit</td></tr>
<tr><td>yes / no / please / thank you</td><td>oui / non / s'il vous plaît / merci</td></tr></table>
""",

"encyclopedia": """
<p>Full English and Spanish Wikipedia are the largest libraries in this kit. The <b>nopic</b> flavour drops images to save space: about 50 GB (EN) and 15 GB (ES). The <b>mini</b> flavour (intro paragraphs only) is a good fallback for small drives.</p>
<p>Search tip: in the Kiwix reader, use the search box at the top. Full-text search works even with no internet.</p>
""",

"translator": """
<p>No machine translator runs inside a ZIM file, so this kit relies on <b>phrasebooks</b> (Wikivoyage has hundreds: search "<i>Spanish phrasebook</i>") plus dictionaries.</p>
<h2>Survival phrase card</h2>
<table><tr><th>English</th><th>Spanish</th><th>French</th><th>Mandarin</th></tr>
<tr><td>I need help</td><td>Necesito ayuda</td><td>J'ai besoin d'aide</td><td>我需要帮助 wǒ xūyào bāngzhù</td></tr>
<tr><td>Call a doctor</td><td>Llame a un médico</td><td>Appelez un médecin</td><td>请叫医生 qǐng jiào yīshēng</td></tr>
<tr><td>Is this water safe?</td><td>¿Es potable esta agua?</td><td>Cette eau est-elle potable ?</td><td>这水能喝吗？ zhè shuǐ néng hē ma?</td></tr>
<tr><td>I am lost</td><td>Estoy perdido/a</td><td>Je suis perdu(e)</td><td>我迷路了 wǒ mílù le</td></tr>
<tr><td>I don't understand</td><td>No entiendo</td><td>Je ne comprends pas</td><td>我不明白 wǒ bù míngbai</td></tr>
<tr><td>Allergic to…</td><td>Soy alérgico/a a…</td><td>Je suis allergique à…</td><td>我对…过敏 wǒ duì… guòmǐn</td></tr></table>
<p>For true offline machine translation, install the free <b>Argos Translate</b> / LibreTranslate desktop app and its language packs onto the drive while you still have internet.</p>
""",

# ---------------------------------------------------------------- survival
"fire": """
<h2>The fire triangle</h2><p>Heat + fuel + oxygen. Prepare all three <b>before</b> you strike anything.</p>
<ol><li><b>Tinder</b> (catches a spark): dry grass, birch bark, cattail fluff, fatwood shavings, char cloth, cotton balls with petroleum jelly.</li>
<li><b>Kindling</b>: pencil-lead up to thumb-thick dead twigs that snap cleanly. Gather twice what you think you need.</li>
<li><b>Fuel</b>: wrist-thick and larger dead, standing wood (wood on the ground is often wet).</li></ol>
<h2>Ignition without matches</h2>
<ul><li><b>Ferro rod</b>: scrape hard with the spine of a knife, close to tinder. Works wet.</li>
<li><b>Bow drill</b>: dry softwood (cedar, willow, basswood) hearth board and spindle; notch beside the depression; steady full-length strokes until an ember forms in the notch; tip into tinder bundle and blow gently.</li>
<li><b>Battery + steel wool</b>: touch both 9 V terminals to fine steel wool.</li>
<li><b>Lens</b>: magnifying glass, eyeglasses, or a clear bag of water focused to the smallest point on dark tinder.</li>
<li><b>Flint &amp; steel</b>: strike high-carbon steel against flint onto char cloth.</li></ul>
<h2>Lays</h2><p><b>Teepee</b> for fast heat/light; <b>log cabin</b> for cooking coals; <b>lean-to</b> against a log in wind.</p>
""" + WARN.format("Clear 3 m around the fire down to mineral soil. Never use fire, stoves or charcoal inside a sealed shelter or bunker without ventilation: carbon monoxide kills silently."),

"fishing": """
<h2>Improvised gear</h2>
<ul><li>Hooks: safety pins, thorns, bent wire, carved wood "gorge" (a sliver sharpened at both ends that toggles in the throat).</li>
<li>Line: inner strands of paracord, dental floss, plant fibre cordage.</li>
<li>Bait: worms, grubs, insects, bits of guts from previous catch.</li></ul>
<h2>Where fish hold</h2>
<p>Eddies behind rocks, undercut banks, deep pools below riffles, shade, and inflows. Fish early morning and evening; in heat, fish deeper.</p>
<h2>Passive methods (work while you do other things)</h2>
<ul><li><b>Trotline</b>: several baited hooks on droppers along a line staked across a stream.</li>
<li><b>Fish trap / weir</b>: funnel of stones or stakes leading into an enclosure in shallow water.</li>
<li><b>Gill net</b> from cordage, set across slow current.</li></ul>
<p>Check local law: many methods are illegal where fishing is regulated.</p>
<h2>Cleaning</h2><p>Stun, then cut behind the gills. Slit belly from vent to gills, remove guts, scrape the bloodline along the spine. Cook freshwater fish thoroughly (parasites).</p>
""",

"hunting": """
<h2>Fundamentals</h2>
<ul><li><b>Scout</b> first: tracks, trails, beds, feeding areas, water. See <a href="tracking.html">Tracking</a>.</li>
<li><b>Wind</b>: keep it in your face. Animals smell you long before they see you.</li>
<li><b>Move slowly</b>: a few steps, then stop and look for a minute. Most game is seen first by its movement or ear flick.</li>
<li><b>Dawn and dusk</b> are prime times.</li></ul>
<h2>Shot placement</h2>
<p>Aim for the heart/lung area: just behind the front shoulder, one-third up from the belly line, on a broadside or slightly quartering-away animal. This is the most ethical and reliable kill zone.</p>
<h2>Small game snares</h2>
<p>A simple wire or cord loop (fist-sized for rabbits) set on a run where it narrows, anchored to a stake. Set many; check daily. See <a href="traps.html">Primal traps</a>.</p>
<h2>After the shot</h2>
<p>Wait 20–30 min before following a wounded animal. Mark the spot, follow blood, look for bright frothy blood (lung) vs dark (liver). Field-dress promptly: see <a href="butchering.html">Butchering</a>.</p>
""" + WARN.format("Know and follow local hunting law and seasons wherever they still apply. Positively identify the target and what is behind it."),

"preserve-wild": """
<p>Bacteria need warmth, moisture and time. Remove one and food lasts.</p>
<table><tr><th>Method</th><th>How</th><th>Keeps</th></tr>
<tr><td>Drying / jerky</td><td>Lean meat sliced 5 mm thick, salted, dried in sun, wind or near fire until it cracks when bent.</td><td>1–2 months</td></tr>
<tr><td>Smoking</td><td>See <a href="smoking.html">How to smoke foods</a>.</td><td>Weeks to months</td></tr>
<tr><td>Salting</td><td>Pack meat or fish in dry salt (about 1 part salt : 4 parts meat) in layers; drain liquid.</td><td>Months</td></tr>
<tr><td>Pemmican</td><td>Dry meat ground to powder + equal weight rendered fat (+ dried berries).</td><td>Months to years</td></tr>
<tr><td>Cold storage</td><td>Streams, root cellar, buried crocks below frost line; snow pit in winter.</td><td>Days to months</td></tr>
<tr><td>Living storage</td><td>Keep fish in a pen, leave root crops in the ground.</td><td>Indefinite</td></tr></table>
<p>Store dried food in sealed containers away from moisture and rodents. Hang meat bags 4 m up and 2 m from a trunk in bear country.</p>
""",

"canning": """
<h2>Two methods: choose by acidity</h2>
<table><tr><th>Food</th><th>Method</th></tr>
<tr><td>High acid: fruit, jam, pickles, tomatoes <i>with added acid</i></td><td>Boiling water bath</td></tr>
<tr><td>Low acid: vegetables, beans, meat, fish, soups</td><td><b>Pressure canner only</b> (about 10–15 psi, 116–121 °C)</td></tr></table>
<h2>Water bath steps</h2>
<ol><li>Wash jars; keep hot. Use new lids.</li><li>Fill, leaving the headspace your recipe states (usually 6–13 mm).</li>
<li>Remove air bubbles; wipe rims; fit lids finger-tight.</li><li>Submerge 2–3 cm under boiling water; time from when it returns to a full boil.</li>
<li>Cool 12–24 h undisturbed. The lid should not flex when pressed.</li></ol>
<p>For tomatoes add 1 tbsp bottled lemon juice per pint (2 tbsp per quart). Add processing time at altitude.</p>
""" + WARN.format("Botulism toxin has no smell or taste. Never water-bath or oven-can low-acid foods. Discard bulging, leaking, spurting or foul jars without tasting. Boiling home-canned low-acid food for 10 minutes before eating adds a margin of safety."),

"smoking": """
<h2>Hot vs cold smoking</h2>
<table><tr><th></th><th>Hot smoking</th><th>Cold smoking</th></tr>
<tr><td>Temperature</td><td>80–110 °C</td><td>under 30 °C</td></tr>
<tr><td>Result</td><td>Cooked, eat within days or dry further</td><td>Flavoured &amp; dried, needs prior curing</td></tr>
<tr><td>Safety</td><td>Cook to safe core temp (poultry 74 °C, pork 63 °C, fish 63 °C)</td><td>Only for well-salted/cured food</td></tr></table>
<h2>Improvised smoker</h2>
<ol><li>Build a tripod or frame of green sticks about 1 m tall with racks of green (live) wood.</li>
<li>Wrap with bark, tarp, or leafy branches leaving a small vent at the top.</li>
<li>Small fire of hardwood coals; smother with green wood chips for smoke. Avoid resinous conifers (bitter soot).</li>
<li>Slice meat/fish thin; salt or brine first (1 cup salt per gallon water, 1–12 h).</li>
<li>Smoke until dry and leathery: 12–48 h for long-keeping fish.</li></ol>
<p>Good woods: hickory, oak, maple, apple, cherry, alder (fish), mesquite.</p>
""",

"water": """
<p>Treat <b>all</b> wild water. Clear-looking water can carry Giardia, Cryptosporidium, bacteria and viruses.</p>
<h2>1. Pre-filter</h2><p>Let it settle, then pour through cloth, a bandana, or a coffee filter. A layered filter (gravel → sand → charcoal → sand → cloth) removes sediment and improves taste but <b>does not make water safe</b> on its own.</p>
<h2>2. Disinfect: pick one</h2>
<table><tr><th>Method</th><th>Dose</th></tr>
<tr><td>Boiling</td><td>Rolling boil 1 minute (3 minutes above 2,000 m).</td></tr>
<tr><td>Unscented household bleach (6–8.25%)</td><td>2 drops per litre (8 drops per gallon). Double if cloudy or cold. Wait 30 min; should smell faintly of chlorine.</td></tr>
<tr><td>Iodine tincture 2%</td><td>5 drops per litre; wait 30 min. Not for pregnancy or thyroid issues.</td></tr>
<tr><td>Chlorine dioxide tablets</td><td>Per package; kills Crypto with a 4 h wait.</td></tr>
<tr><td>SODIS (solar)</td><td>Clear PET bottle, ≤2 L, in full sun 6 h (2 days if cloudy).</td></tr>
<tr><td>Commercial filter</td><td>0.2 µm or smaller pore size for bacteria/protozoa. Most do not stop viruses.</td></tr></table>
<h2>Finding water</h2><p>Follow green vegetation, animal trails heading downhill, insects/birds at dusk. Dig at the outside bend of dry riverbeds. Collect rain and dew (cloth dragged through grass at dawn). Snow must be melted, not eaten.</p>
""" + WARN.format("Chemical contamination (fuel, mine runoff, agricultural chemicals) is NOT removed by boiling. Activated charcoal helps only partly; find another source."),

"shelter": """
<h2>Priorities (rule of 3s)</h2><p>About 3 hours without shelter in harsh weather, 3 days without water, 3 weeks without food. Shelter comes first when it's cold, wet or windy.</p>
<h2>Site selection</h2><ul><li>Flat, dry, out of the wind, near (not next to) water and materials.</li>
<li>Avoid dry creek beds (flash floods), dead trees overhead ("widowmakers"), hilltops (lightning), and valley floors (cold air pools).</li></ul>
<h2>Debris hut (no tools)</h2>
<ol><li>Ridgepole about 1.5× your height, one end on a stump or forked stick at hip height.</li>
<li>Lean sticks along both sides like ribs, close together.</li>
<li>Pile leaves, grass, pine needles at least an arm's length (60–90 cm) thick over the frame.</li>
<li>Stuff the inside with dry debris too. You heat the small space with your body.</li></ol>
<h2>Other designs</h2><ul><li><b>Lean-to + reflector fire</b>: open side faces the fire; stack logs behind the fire to bounce heat in.</li>
<li><b>Tarp A-frame</b>: line between two trees, tarp over, stake corners.</li>
<li><b>Snow trench / quinzhee</b>: in deep snow; poke a ventilation hole.</li></ul>
<p><b>Insulate from the ground</b>: you lose more heat to the ground than the air. Use 15 cm+ of boughs or leaves.</p>
""",

"irrigation": """
<h2>How much water</h2><p>Most vegetables need about 2.5 cm (1 inch) of water per week, more in heat or sandy soil. Water deeply and less often to push roots down.</p>
<h2>Timing</h2><p>Early morning is best (less evaporation, leaves dry before night). Water the soil, not the leaves, to avoid fungal disease.</p>
<h2>Low-tech systems</h2>
<table><tr><th>System</th><th>Notes</th></tr>
<tr><td>Ollas</td><td>Unglazed clay pots buried to the neck and filled; water seeps to roots. Very efficient.</td></tr>
<tr><td>Gravity drip</td><td>Barrel raised 1–2 m feeding a hose with pinholes or emitters. No pump needed.</td></tr>
<tr><td>Soaker / bottle drip</td><td>Plastic bottles with a pinhole in the cap, buried upside down by the plant.</td></tr>
<tr><td>Swales</td><td>Shallow ditches on contour that catch runoff and soak it into the soil.</td></tr>
<tr><td>Rain harvesting</td><td>1 mm of rain on 1 m² of roof = 1 litre. A 100 m² roof yields 2,500 L from a 25 mm storm.</td></tr>
<tr><td>Wicking beds</td><td>Raised bed over a gravel water reservoir; soil wicks moisture up.</td></tr></table>
<p>Mulch 5–10 cm deep (straw, leaves, wood chips) cuts water use by up to half.</p>
""",

# ---------------------------------------------------------------- supplemental
"sewing": """
<h2>Essential hand stitches</h2>
<ul><li><b>Running stitch</b>: in-and-out in a line. Fast basting and gathering.</li>
<li><b>Backstitch</b>: each stitch goes back to the end of the previous one. Strongest hand seam; use it for repairs.</li>
<li><b>Whip / overcast stitch</b>: loops over the edge to stop fraying and join edges.</li>
<li><b>Blanket stitch</b>: finishing edges on wool, leather and blankets.</li>
<li><b>Patch</b>: cut 2 cm larger than hole, fold edges under, backstitch all round.</li></ul>
<p>Use doubled thread and knot the end. Waxing thread (beeswax, candle) stops tangling and adds water resistance.</p>
<h2>Making cordage and thread</h2><p>Strip fibres from dogbane, nettle, milkweed, yucca or the inner bark of basswood/cedar. <b>Reverse-wrap</b>: twist two bundles clockwise each, then wrap them around each other counter-clockwise.</p>
<h2>Simple weaving</h2><p>Set up a frame loom (four sticks lashed in a rectangle), wind the <i>warp</i> threads tightly top-to-bottom, then pass the <i>weft</i> over-under across, alternating each row, packing tight with a comb or fork. Use the same over-under method to weave baskets and mats from willow, reeds or cattail leaves.</p>
""",

"knots": """
<table><tr><th>Knot</th><th>Use</th><th>How</th></tr>
<tr><td>Square (reef)</td><td>Joining two ends of the same rope (bandages, bundles)</td><td>Right over left, left over right. Not for load-bearing.</td></tr>
<tr><td>Bowline</td><td>Fixed loop that won't slip; rescue loop</td><td>"Rabbit comes out of the hole, round the tree, back down the hole."</td></tr>
<tr><td>Clove hitch</td><td>Quick attach to a post; start of lashings</td><td>Two half-turns crossing over themselves.</td></tr>
<tr><td>Taut-line hitch</td><td>Adjustable tent/tarp guylines</td><td>Two turns inside the loop, one outside, around the standing part.</td></tr>
<tr><td>Trucker's hitch</td><td>Tightening loads and ridgelines with 3:1 advantage</td><td>Slipped loop in the standing part, through anchor, back through loop, pull and tie off.</td></tr>
<tr><td>Sheet bend</td><td>Joining two different ropes</td><td>Bight in the thicker, thinner goes up through, around, and under itself.</td></tr>
<tr><td>Figure-eight</td><td>Stopper; with follow-through, climbing tie-in</td><td>Loop, twist once, pass end through.</td></tr>
<tr><td>Prusik</td><td>Grips a rope; ascending, adjustable anchors</td><td>Loop of thinner cord wrapped 3× around the main rope through itself.</td></tr></table>
<h2>Lashings</h2><p><b>Square lashing</b> joins crossing poles (start/end with clove hitch, 3–4 wraps, then frapping turns). <b>Tripod lashing</b> builds tripods for cooking and smoking racks.</p>
""",

"firearms": """
<h2>The four rules: always, every time</h2>
<ol><li>Treat every firearm as if it is loaded.</li>
<li>Never point the muzzle at anything you are not willing to destroy.</li>
<li>Keep your finger off the trigger and outside the guard until your sights are on target and you have decided to shoot.</li>
<li>Be sure of your target and what is behind it.</li></ol>
<h2>Fundamentals of accurate shooting</h2>
<ul><li><b>Stance/position</b>: stable, supported where possible (prone is steadiest).</li>
<li><b>Sight alignment</b>: front sight centred in rear notch, tops level; focus on the front sight.</li>
<li><b>Breathing</b>: shoot during the natural pause after exhaling.</li>
<li><b>Trigger press</b>: smooth steady press straight back; let the shot "surprise" you.</li>
<li><b>Follow-through</b>: hold position after the shot.</li></ul>
<h2>Maintenance &amp; storage</h2>
<p>Unload and verify (look and feel the chamber) before cleaning. Clean the bore and action after use and after exposure to rain. Light oil prevents rust. Store unloaded, locked, ammunition separate, out of reach of children.</p>
<h2>Malfunction</h2><p>If a round fails to fire, keep the muzzle pointed safely for at least 30 seconds (possible hang-fire) before opening the action.</p>
""" + WARN.format("Seek hands-on instruction from a qualified instructor. Know the laws where you are."),

"swimming": """
<h2>If you fall in cold water: 1-10-1</h2><p>1 minute of gasping (keep your head up, don't panic), 10 minutes of useful movement to get out, about 1 hour before hypothermia makes you unconscious. Get out or onto something that floats.</p>
<h2>Float first</h2>
<ul><li><b>Back float</b>: lie back, ears in the water, chest up, arms out, small sculling motions. Breathe normally.</li>
<li><b>Treading water</b>: upright, slow eggbeater or scissor kick, hands sweeping flat side to side.</li></ul>
<h2>Learning strokes</h2>
<ol><li>Get comfortable with your face in the water; blow bubbles out through your nose.</li>
<li>Glide: push off a wall face-down, arms forward, body straight.</li>
<li>Add a flutter kick from the hips with loose ankles.</li>
<li><b>Breaststroke</b> is the most energy-efficient survival stroke and keeps your head up to see.</li></ol>
<h2>Rip currents</h2><p>Don't fight it. Swim parallel to the shore until free, then angle back. Or float and signal.</p>
<h2>Rescuing others</h2><p><b>Reach, throw, don't go</b>: offer a branch or throw something that floats. A panicking swimmer can drown a rescuer.</p>
""",

"archery": """
<h2>Basic shot cycle</h2>
<ol><li><b>Stance</b>: feet shoulder-width, perpendicular to the target.</li>
<li><b>Nock</b> the arrow under the nocking point, index fletching away from the bow.</li>
<li><b>Grip</b>: relaxed, pressure on the meaty pad of the thumb, no strangling.</li>
<li><b>Draw</b>: three fingers (one above, two below the arrow) using back muscles, bow arm straight but not locked.</li>
<li><b>Anchor</b>: same spot every time (corner of mouth or under jaw).</li>
<li><b>Aim and release</b>: relax the fingers; let the string slip away. Hold your follow-through.</li></ol>
<h2>Making a survival bow</h2>
<ul><li>Wood: dead-straight, knot-free stave of hickory, ash, osage orange, yew or elm, about your height.</li>
<li>Shape the belly (side facing you) so both limbs bend evenly; leave the back (facing target) as the outer growth ring.</li>
<li>Season green wood several weeks if you can. "Tiller" slowly: bend, check, remove wood where stiff.</li>
<li>String: strong cordage, sinew, or rawhide.</li>
<li>Arrows: straight shoots (dogwood, cane, viburnum) straightened over heat; fletch with three feathers; fire-harden or knap stone points.</li></ul>
""" + WARN.format("Never dry-fire (release the string without an arrow); it can shatter the bow."),

# ---------------------------------------------------------------- tech
"electrical": """
<h2>Core formulas</h2>
<ul><li><b>Ohm's law</b>: V = I × R (volts = amps × ohms)</li>
<li><b>Power</b>: W = V × I. A 60 W load on 12 V draws 5 A.</li>
<li><b>Energy</b>: Wh = W × hours. A 100 Ah 12 V battery stores about 1,200 Wh (usable about 600 Wh for lead-acid at 50% depth, 1,000 Wh+ for LiFePO4).</li></ul>
<h2>Small solar system</h2>
<p>Panel → charge controller (MPPT preferred) → battery → fuse → loads / inverter. Size panels for about 1.5× your daily Wh ÷ peak sun hours (typically 3–6).</p>
<h2>Wire sizing (12 V DC, ≤3% drop, about 3 m run)</h2>
<table><tr><th>Current</th><th>Copper wire</th></tr><tr><td>up to 10 A</td><td>14 AWG / 2.5 mm²</td></tr>
<tr><td>up to 20 A</td><td>10 AWG / 6 mm²</td></tr><tr><td>up to 40 A</td><td>6 AWG / 16 mm²</td></tr></table>
<p>Low voltage = high current = thicker wire. Fuse every positive lead close to the battery.</p>
<h2>Safety</h2><ul><li>Turn off and <b>verify dead</b> with a tester before touching.</li><li>Mains AC (120/230 V) can kill; DC battery banks can arc and weld.</li>
<li>Never bypass a fuse with wire or foil. Ventilate lead-acid batteries (hydrogen gas).</li></ul>
""",

"mechanic": """
<h2>Won't start? Diagnose in order</h2>
<table><tr><th>Symptom</th><th>Likely cause</th></tr>
<tr><td>Nothing / clicking</td><td>Dead battery, corroded terminals. Clean with baking soda + water, tighten, jump.</td></tr>
<tr><td>Cranks, no start</td><td>No fuel (pump, filter), no spark (plugs, coil), flooded.</td></tr>
<tr><td>Starts then dies</td><td>Fuel delivery, air leak, clogged air filter.</td></tr>
<tr><td>Overheating</td><td>Low coolant, broken belt, stuck thermostat. Never open a hot radiator cap.</td></tr></table>
<h2>Jump-starting</h2><p>Red to dead +, red to good +, black to good −, black to bare metal on dead car (not battery −). Start good car, wait 2 min, start dead car. Remove in reverse.</p>
<h2>Routine maintenance</h2><ul><li>Oil and filter every 5,000–10,000 km; check level weekly.</li>
<li>Tyre pressure monthly; rotate tyres; check tread.</li><li>Air filter, coolant, brake fluid, belts, wiper blades.</li></ul>
<h2>Changing a tyre</h2><p>Park flat, handbrake, wedge wheels. Loosen nuts half a turn <i>before</i> jacking. Jack at the frame point, swap, hand-tighten nuts in a star pattern, lower, then torque fully.</p>
<p>Long-term storage: fuel stabiliser, battery tender or disconnect, full tank to limit condensation.</p>
""",

"walkie": """
<p>The simplest DIY two-way radio uses licence-free or amateur bands. Building from scratch is an advanced electronics project. Practical paths:</p>
<h2>Option A: Program cheap handhelds (easiest)</h2>
<p>Inexpensive VHF/UHF handhelds can be programmed with free software (CHIRP) and a USB cable. Licensing: FRS (US) and PMR446 (EU) need no licence. GMRS and amateur bands need one where enforced.</p>
<h2>Option B: Build a simple AM/FM transmitter + receiver</h2>
<ul><li><b>Receiver</b>: crystal radio (coil, variable capacitor, germanium diode, high-impedance earpiece, long wire antenna, ground). Needs no power.</li>
<li><b>Transmitter</b>: a single-transistor FM oscillator (e.g. 2N3904, coil, trimmer cap, microphone) transmits a few tens of metres. Extending range legally means a licence.</li></ul>
<h2>Antennas make the most difference</h2>
<p>Quarter-wave length (m) ≈ 75 ÷ frequency (MHz). For 146 MHz: about 51 cm. Get the antenna as high as possible; height beats power.</p>
<h2>Kit list</h2><p>Soldering iron, solder, multimeter, assorted resistors/capacitors, transistors, diodes, 9 V batteries, coax, BNC/SMA connectors.</p>
""",

"radio": """
<h2>Bands at a glance</h2>
<table><tr><th>Service</th><th>Range</th><th>Licence</th></tr>
<tr><td>FRS / PMR446 handhelds</td><td>1–3 km</td><td>None</td></tr>
<tr><td>GMRS (US)</td><td>5–30 km with repeaters</td><td>Simple licence, no test</td></tr>
<tr><td>CB 27 MHz</td><td>5–25 km, far further in good conditions</td><td>None in most places</td></tr>
<tr><td>Amateur 2 m / 70 cm</td><td>Local + repeaters</td><td>Exam</td></tr>
<tr><td>Amateur HF (80–10 m)</td><td>Regional to worldwide</td><td>Exam</td></tr></table>
<p>In a genuine life-threatening emergency, most regulations allow anyone to use any frequency to call for help.</p>
<h2>Calling for help</h2>
<p>"<b>MAYDAY MAYDAY MAYDAY</b>, this is [name], [location], [nature of emergency], [number of people], [assistance needed]. Over." Use <i>PAN-PAN</i> for urgent but not life-threatening.</p>
<h2>Useful frequencies (US examples)</h2>
<ul><li>CB channel 9: emergency; channel 19: highway traffic.</li><li>FRS/GMRS channel 1 or 3: common rally points.</li>
<li>146.520 MHz: 2 m national simplex calling.</li><li>Marine VHF channel 16: distress (156.8 MHz).</li><li>NOAA weather radio: 162.400–162.550 MHz.</li></ul>
<h2>Discipline</h2><p>Listen first. Keep transmissions short. Use the phonetic alphabet (Alfa, Bravo, Charlie…). Set a daily schedule (e.g. top of each hour for 5 min) to save batteries.</p>
""",

# ---------------------------------------------------------------- first aid
"natural-medicine": """
<p>Traditional remedies with reasonable evidence for <b>mild</b> problems. They don't replace real medicine for serious illness.</p>
<table><tr><th>Plant</th><th>Traditional use</th><th>Preparation &amp; cautions</th></tr>
<tr><td>Plantain (Plantago)</td><td>Stings, bites, minor cuts</td><td>Chew or crush leaf, apply as a poultice.</td></tr>
<tr><td>Yarrow</td><td>Slows minor bleeding</td><td>Crushed leaf on wound. Allergy risk (daisy family).</td></tr>
<tr><td>Willow bark</td><td>Pain, fever (contains salicin)</td><td>Tea from inner bark. Avoid with aspirin allergy, children, bleeding disorders.</td></tr>
<tr><td>Ginger</td><td>Nausea, motion sickness</td><td>Fresh root tea.</td></tr>
<tr><td>Peppermint</td><td>Indigestion, headache</td><td>Tea; oil diluted on temples.</td></tr>
<tr><td>Honey (raw)</td><td>Wound dressing, sore throat</td><td>Antibacterial. Never for infants under 1 year.</td></tr>
<tr><td>Garlic</td><td>Mild antimicrobial</td><td>Eat raw. Do not apply raw to skin (burns).</td></tr>
<tr><td>Aloe vera</td><td>Minor burns, sunburn</td><td>Gel from inside the leaf.</td></tr>
<tr><td>Chamomile</td><td>Sleep, anxiety, stomach</td><td>Tea. Daisy-family allergy risk.</td></tr>
<tr><td>Activated charcoal</td><td>Some ingested poisons</td><td>Only if advised. Not for corrosives or alcohol.</td></tr></table>
<p><b>Oral rehydration solution</b> for diarrhoea: 1 L clean water + 6 level tsp sugar + ½ level tsp salt.</p>
""",

"first-aid": """
<h2>Primary survey: DRSABC</h2>
<ol><li><b>Danger</b>: protect yourself first.</li><li><b>Response</b>: talk, tap shoulders.</li>
<li><b>Send for help</b> if possible.</li><li><b>Airway</b>: head tilt, chin lift.</li>
<li><b>Breathing</b>: look, listen, feel for up to 10 seconds. Not breathing normally → <a href="cpr.html">CPR</a>.</li>
<li><b>Circulation</b>: find and stop major bleeding (see <a href="wounds.html">wounds</a>).</li></ol>
<h2>Common emergencies</h2>
<table><tr><th>Problem</th><th>Do</th></tr>
<tr><td>Shock (pale, clammy, fast pulse)</td><td>Lay down, legs raised if no injury, keep warm, nothing by mouth.</td></tr>
<tr><td>Fracture</td><td>Splint in the position found, including joints above and below. Check circulation beyond.</td></tr>
<tr><td>Sprain</td><td>Rest, ice/cold (20 min), compression, elevation.</td></tr>
<tr><td>Hypothermia</td><td>Remove wet clothes, insulate from ground, warm the core, warm sweet drinks if alert. Handle gently.</td></tr>
<tr><td>Heat stroke (hot, confused)</td><td>Cool aggressively: shade, wet the skin, fan, ice packs to neck/armpits/groin.</td></tr>
<tr><td>Allergic reaction / anaphylaxis</td><td>Epinephrine auto-injector into outer thigh; repeat after 5–15 min if no improvement.</td></tr>
<tr><td>Seizure</td><td>Protect head, time it, nothing in mouth, recovery position after.</td></tr></table>
<h2>Recovery position</h2><p>For an unconscious casualty who is breathing: roll onto side, top knee bent forward, head tilted back so fluids drain.</p>
<h2>Kit</h2><p>Gloves, trauma dressings, gauze, tape, tourniquet, SAM splint, triangular bandages, shears, tweezers, saline, antiseptic, pain relievers, antihistamine, ORS, space blanket.</p>
""",

"cpr": """
<p class="warn">If someone is unresponsive and not breathing normally (gasping doesn't count), start CPR immediately.</p>
<h2>Adult CPR</h2>
<ol><li>Lay them flat on their back on a firm surface.</li>
<li>Heel of one hand on the centre of the chest (lower half of the breastbone), other hand on top, arms straight.</li>
<li><b>Push hard and fast</b>: 5–6 cm deep, 100–120 per minute (beat of "Stayin' Alive"). Let the chest fully recoil.</li>
<li>If trained: after 30 compressions, give <b>2 rescue breaths</b> (head tilt, chin lift, pinch nose, 1 second each, watch chest rise). Otherwise do <b>hands-only</b> continuous compressions.</li>
<li>Continue 30:2 until they breathe, an AED arrives, help takes over, or you are exhausted.</li></ol>
<h2>AED</h2><p>Turn it on and follow the voice prompts. Bare, dry chest. Don't touch the person during analysis or shock.</p>
<h2>Children and infants</h2>
<table><tr><th></th><th>Child (1–puberty)</th><th>Infant (&lt;1 yr)</th></tr>
<tr><td>Start with</td><td colspan="2">5 rescue breaths if trained (cause is usually breathing)</td></tr>
<tr><td>Compress with</td><td>1 or 2 hands</td><td>2 fingers or two thumbs encircling</td></tr>
<tr><td>Depth</td><td>About 5 cm (⅓ of chest)</td><td>About 4 cm (⅓ of chest)</td></tr>
<tr><td>Ratio</td><td colspan="2">30:2 (single rescuer)</td></tr></table>
<h2>Drowning</h2><p>Give 5 initial rescue breaths, then 30:2.</p>
""",

"choking": """
<h2>Adult or child over 1 year</h2>
<p><b>Mild</b> (coughing, can speak): encourage coughing. Don't hit them.</p>
<p><b>Severe</b> (can't speak, cough or breathe; clutching throat):</p>
<ol><li><b>5 back blows</b>: lean them forward, hit firmly between the shoulder blades with the heel of your hand.</li>
<li><b>5 abdominal thrusts (Heimlich)</b>: stand behind, fist just above the navel (thumb side in), other hand over it, sharp inward-and-upward pulls.</li>
<li>Alternate 5 and 5 until the object comes out or they become unresponsive.</li>
<li>If unresponsive: lower to the ground and start <a href="cpr.html">CPR</a>. Look in the mouth before breaths and remove any visible object (no blind finger sweeps).</li></ol>
<p><b>Pregnant or obese</b>: use chest thrusts (hands on the centre of the breastbone) instead of abdominal thrusts.</p>
<p><b>Alone?</b> Thrust your abdomen against the back of a chair or a counter edge.</p>
<h2>Infant (under 1 year)</h2>
<ol><li>Lay face-down along your forearm, head lower, supporting the jaw. <b>5 back blows</b>.</li>
<li>Turn face-up, head lower. <b>5 chest thrusts</b> with two fingers on the centre of the chest.</li>
<li>Repeat. If unresponsive, start infant CPR.</li></ol>
<p>Anyone who received abdominal thrusts should be checked by a medic afterwards (internal injury risk).</p>
""",

"wounds": """
<h2>1. Stop the bleeding</h2>
<ol><li>Gloves or a plastic bag over your hands.</li>
<li><b>Direct pressure</b> with a dressing, hard, for 10+ minutes without peeking.</li>
<li>Deep wound in the junction (groin, armpit, neck)? <b>Pack</b> it tightly with gauze or clean cloth, then press.</li>
<li><b>Tourniquet</b> for life-threatening limb bleeding: 5–8 cm above the wound (not on a joint), tighten until bleeding stops, note the time. Don't loosen it in the field.</li></ol>
<h2>2. Clean</h2><p>Once bleeding is controlled, irrigate with plenty of clean (boiled and cooled, or drinkable) water under pressure, e.g. from a bag with a pinhole. Remove visible dirt with tweezers.</p>
<h2>3. Close or leave open?</h2>
<ul><li>Clean, straight, fresh cuts (under 6–8 h): close with tape or butterfly strips.</li>
<li>Bites, punctures, dirty or old wounds: <b>leave open</b>, pack loosely, and dress. Closing them traps infection.</li></ul>
<h2>4. Dress and watch</h2><p>Cover with a non-stick dressing; change daily or when soaked. Infection signs: spreading redness, swelling, heat, pus, red streaks, fever. Raw honey can be used as a dressing if antibiotic ointment runs out.</p>
<p>Tetanus risk is high in soil and rust wounds. Keep vaccinations current before you go off-grid.</p>
""",

"burns": """
<h2>Immediately</h2>
<ol><li>Stop the burning: remove from source; "stop, drop and roll" for clothing fires.</li>
<li><b>Cool with cool running water for 20 minutes</b>, even up to 3 hours after the burn. Not ice, butter, oil or toothpaste.</li>
<li>Remove rings, watches and clothing near the burn (not anything stuck to it).</li>
<li>Cover loosely with cling film (lay it on, don't wrap) or a clean non-fluffy dressing.</li>
<li>Keep the person warm; cooling a large area can cause hypothermia.</li></ol>
<h2>How bad is it?</h2>
<table><tr><th>Depth</th><th>Looks like</th><th>Care</th></tr>
<tr><td>Superficial</td><td>Red, painful, no blisters</td><td>Cool, aloe, pain relief</td></tr>
<tr><td>Partial thickness</td><td>Blisters, very painful, wet</td><td>Cool, don't pop blisters, dress, watch for infection</td></tr>
<tr><td>Full thickness</td><td>White, leathery or charred, may be painless</td><td>Serious: cover, treat for shock, evacuate</td></tr></table>
<p>Seek urgent care for burns larger than the casualty's palm, on the face, hands, feet, genitals or joints, encircling a limb, chemical or electrical burns, and smoke inhalation.</p>
<p><b>Chemical</b>: brush off powder, then flush 20+ minutes. <b>Electrical</b>: cut power before touching; check for cardiac arrest.</p>
""",

# ---------------------------------------------------------------- food prep
"butchering": """
<h2>Field dressing a deer-sized animal</h2>
<ol><li>Gloves on. Lay it on its back, head uphill.</li>
<li>Cut a shallow slit from the pelvis to the breastbone, blade edge up, two fingers lifting the skin to avoid puncturing the gut.</li>
<li>Cut around the anus and tie it off. Cut the diaphragm, reach up and sever the windpipe.</li>
<li>Roll the animal to the side and pull the organs out. Keep heart and liver (check the liver for spots or worms).</li>
<li>Drain, prop the cavity open, and cool the carcass fast: shade, airflow, or quarters in cold water bags.</li></ol>
<h2>Skinning &amp; quartering</h2><p>Hang by the hind legs (gambrel). Cut around the hocks, down the inside of the legs, and pull the hide down. Remove front shoulders (no bone joint, just cut under), backstraps along the spine, tenderloins inside, and hindquarters at the ball joint.</p>
<h2>Small game</h2><p>Rabbit: pinch the back skin, cut a slit, pull both ways like a glove. Remove head and feet, open the belly, scoop out organs. Discard any rabbit with spotted liver (tularaemia).</p>
<h2>Filleting fish</h2><p>Cut behind the gill plate to the spine, turn the blade flat and slice along the backbone to the tail. Flip, repeat. Skin by holding the tail end and sliding the knife between skin and flesh.</p>
<p>Keep the knife sharp. A dull knife slips. Wash hands and tools; keep meat below 4 °C or preserve it within hours.</p>
""",

"wild-cookbook": """
<h2>Bannock (camp bread)</h2><p>2 cups flour, 1 tsp baking powder, ½ tsp salt, 2 tbsp fat, water to a stiff dough. Fry in a pan or wrap around a green stick over coals until it sounds hollow.</p>
<h2>Ash-roasted fish</h2><p>Wrap gutted fish in wet leaves (non-toxic: grape, sorrel, burdock) or clay, bury in coals 10–20 min.</p>
<h2>Stone-boiled stew</h2><p>No pot? Line a hole with hide or bark, fill with water and food, drop in fire-heated stones. Avoid river stones; trapped water makes them explode.</p>
<h2>Wild greens sauté</h2><p>Nettles (blanch to remove sting), lamb's quarters, dandelion, chickweed, wood sorrel, cooked in fat with wild garlic.</p>
<h2>Acorn flour</h2><p>Shell, grind, and leach in running water or many changes of water until no longer bitter (tannins). Dry and use as flour.</p>
<h2>Cattail</h2><p>Young shoots raw or cooked like cucumber; green flower heads boiled like corn; root starch pounded and rinsed out.</p>
<h2>Pemmican</h2><p>Equal weights finely powdered dried meat and rendered fat, plus dried berries. Press into cakes. See <a href="preserve-wild.html">Preserving food</a>.</p>
<p>Cook wild game thoroughly: bear and wild boar to 71 °C (trichinosis).</p>
""",

"tea": """
<p>Steep 1 tbsp fresh (1 tsp dried) per cup of hot water, covered, 5–10 minutes. Roots and bark: simmer 15–20 min (decoction).</p>
<table><tr><th>Tea</th><th>Recipe</th><th>Notes</th></tr>
<tr><td>Pine needle</td><td>Handful of chopped green needles, steep (don't boil)</td><td>High in vitamin C. <b>Avoid yew (deadly), Norfolk pine, ponderosa</b>; not in pregnancy.</td></tr>
<tr><td>Mint</td><td>Fresh leaves</td><td>Digestion, cooling.</td></tr>
<tr><td>Rose hip</td><td>Crushed hips, simmer, strain hairs through cloth</td><td>Very high vitamin C.</td></tr>
<tr><td>Nettle</td><td>Dried leaves</td><td>Minerals; wear gloves to harvest.</td></tr>
<tr><td>Chamomile</td><td>Flower heads</td><td>Sleep and calm.</td></tr>
<tr><td>Ginger-honey</td><td>Sliced root simmered, add honey and lemon/sumac</td><td>Colds, nausea.</td></tr>
<tr><td>Spruce tip</td><td>Bright green spring tips</td><td>Citrusy, vitamin C.</td></tr>
<tr><td>Chaga</td><td>Chunk of birch fungus, simmer 1 h+</td><td>Earthy coffee substitute. Reuse chunks.</td></tr>
<tr><td>Dandelion "coffee"</td><td>Roasted, ground roots, simmer</td><td>Caffeine-free.</td></tr>
<tr><td>Sumac-ade</td><td>Red sumac berries soaked in cold water, strained</td><td>Lemonade-like.</td></tr></table>
""",

"finding-spices": """
<p>See <a href="spice-plants.html">Plants for spices</a> for the full list. Where to look:</p>
<ul><li><b>Woodland edges and clearings</b>: wild garlic/ramps (spring), garlic mustard, spicebush, wild ginger.</li>
<li><b>Dry, sunny slopes</b>: wild thyme, oregano/marjoram, sage, juniper.</li>
<li><b>Stream banks and wet ground</b>: wild mint, watercress (cook it: liver fluke risk), sweet flag.</li>
<li><b>Disturbed ground</b>: mustards, wild fennel (expert ID), peppergrass (seeds taste like pepper), chicory (roasted root).</li>
<li><b>Coast</b>: sea salt, kelp and dulse (dried and crumbled for umami and salt).</li></ul>
<h2>Drying &amp; storing</h2><p>Harvest in the morning after dew dries. Bundle and hang upside down in a dark, airy spot, or dry on screens. Store whole leaves and seeds in sealed jars away from light; crush just before use.</p>
<h2>Salt substitutes</h2><p>Coltsfoot ash, hickory ash, seaweed. Sodium is vital; sweating heavily without salt leads to cramps and weakness.</p>
""",

# ---------------------------------------------------------------- defense
"wood-tools": """
<p>Hunting and defence tools you can make with a knife and fire.</p>
<h2>Fire-hardened spear</h2>
<ol><li>Straight sapling, 1.5–2 m, wrist-thick (ash, hickory, oak, maple).</li>
<li>Carve a long tapered point from the denser heartwood side.</li>
<li>Harden: hold the tip <i>near</i> (not in) coals, turning, until it browns and dries. Don't char it black; charring weakens it.</li>
<li>Optional: split the end into 4 prongs, wedge apart, and sharpen for a <b>fishing gig</b>.</li></ol>
<h2>Throwing stick (rabbit stick)</h2><p>Dense curved branch about 60 cm long, flattened slightly. Thrown sidearm so it spins and covers a wide area at ground level. Very effective on small game.</p>
<h2>Atlatl (spear-thrower)</h2><p>Board about 60 cm long with a hook or spur at the back end that cups the butt of a light dart (1.5–2 m). Multiplies throwing force several times.</p>
<h2>Club / digging stick / staff</h2><p>A 1.5 m hardwood staff is a walking aid, probe, and defensive tool for keeping animals at a distance. A shorter root-knob club makes a mallet for stakes.</p>
<p>See <a href="archery.html">Bow and arrow</a> for making a bow.</p>
""",

"traps": """
<p>Traps for <b>food</b> and alarms for <b>early warning</b>. Traps built to injure people are illegal almost everywhere and are a danger to your own family, rescuers and neighbours. Use alarms for perimeter security instead.</p>
<h2>Food traps</h2>
<table><tr><th>Trap</th><th>Target</th><th>Build</th></tr>
<tr><td>Simple snare</td><td>Rabbit, squirrel</td><td>Wire or cord loop (fist-sized for rabbit, about 10 cm off the ground) on a narrow trail, anchored to a stake.</td></tr>
<tr><td>Spring snare</td><td>Rabbit</td><td>Snare tied to a bent sapling held by a toggle trigger; lifts the catch off the ground away from scavengers.</td></tr>
<tr><td>Squirrel pole</td><td>Squirrels</td><td>Pole leaned on a tree with several small snares along it.</td></tr>
<tr><td>Figure-4 deadfall</td><td>Mice, squirrels</td><td>Three notched sticks in a "4" shape propping a flat rock; bait on the trigger stick.</td></tr>
<tr><td>Paiute deadfall</td><td>Small game</td><td>Like the figure-4 with a cord-and-toggle trigger; more sensitive.</td></tr>
<tr><td>Funnel fish trap</td><td>Fish</td><td>See <a href="fishing.html">fishing</a>.</td></tr></table>
<p>Set many traps on active runs, handle with gloves or rub with soil/smoke to hide your scent, check at least daily, and mark locations.</p>
<h2>Perimeter alarms (non-harmful)</h2>
<ul><li><b>Tripwire + cans</b>: fishing line at shin height between trees, tied to cans with pebbles.</li>
<li><b>Dry-leaf and stick paths</b>: crunchy ground cover on approaches.</li>
<li><b>Bell or rattle lines</b> around camp at night.</li>
<li><b>Mousetrap + cap or whistle</b>: noise-maker triggered by a line.</li>
<li>Battery motion alarms or driveway sensors if you have power.</li></ul>
""",

"predators": """
<h2>Prevention is most of it</h2>
<ul><li>Cook and store food 100 m downwind of where you sleep. Hang or use bear canisters.</li>
<li>Travel in groups, make noise in thick brush, carry bear spray within reach (not in the pack).</li>
<li>Keep children and pets close; at dawn and dusk especially.</li></ul>
<table><tr><th>Animal</th><th>Encounter</th><th>If attacked</th></tr>
<tr><td>Black bear</td><td>Stand tall, talk firmly, back away; never run or climb</td><td><b>Fight back</b> hard: face and nose</td></tr>
<tr><td>Grizzly / brown bear</td><td>Spray at 10 m, calm voice, back away</td><td>Defensive attack: <b>play dead</b> face-down, hands behind neck, legs spread. If it starts eating you, fight.</td></tr>
<tr><td>Mountain lion / cougar</td><td>Face it, make yourself huge, shout, throw things; never turn your back</td><td>Fight back; protect neck</td></tr>
<tr><td>Wolves / feral dogs</td><td>Stand together, back to a tree or rock, yell, use a staff</td><td>Stay on your feet; fight; protect throat</td></tr>
<tr><td>Moose</td><td>Back off; most dangerous when ears back, hackles up</td><td>Run and get behind a tree; curl up if knocked down</td></tr>
<tr><td>Snakes</td><td>Freeze, then back away slowly</td><td>See <a href="poison.html">Poison guide</a></td></tr>
<tr><td>Alligators / crocodiles</td><td>Stay 10 m+ from water edges</td><td>Fight: eyes and snout; run in a straight line on land</td></tr></table>
<p>Bear spray (capsaicin) outperforms firearms in documented bear encounters. Practise drawing it.</p>
""",
}
