# The dad-jokes cast

Reference art: [`reference/cast-goofy-woofy.png`](reference/cast-goofy-woofy.png)

Two fixed characters, not two anonymous coat colours. Whatever a script calls its
speakers, the **first speaker is drawn as Goofy** and the second as Woofy — the art is
the constant, the names in the dialogue are not.

The canonical definition lives in code, at `CAST` in `web/lib/dogs.ts`. This file is the
character bible behind it; change both together.

## Goofy — the teller

| | |
|---|---|
| Breed | Golden retriever |
| Coat | `(232, 178, 106)` warm gold |
| Collar | `(66, 126, 190)` blue, bone tag reading GOOFY |
| Glasses | Black frames (`outfit="shades"`) |
| Persona | Sunny, over-eager, always has the joke and cannot wait to land it |

Always takes the first line of a beat and the punchline. Draws with `expression="laugh"`
on the punchline.

## Woofy — the straight man

| | |
|---|---|
| Breed | Border collie |
| Coat | `(58, 60, 74)` near-black |
| Markings | `markings="collie"` — white blaze, muzzle, chest, paws and tail tip |
| Collar | `(206, 66, 62)` red, bone tag reading WOOFY |
| Glasses | Red frames (`outfit="redshades"`) |
| Persona | Dry, long-suffering. Sets up the punchline, immediately regrets it |

Woofy carries `expression="smug"` or `"deadpan"` on setup lines.

**They are told apart three ways on purpose** — coat, markings, and collar colour. At
Short size on a phone, coat alone is not enough, which is why the collie markings and the
named tags exist.

## What the toolkit can draw today

`tk.dog()` in `engine/toolkit.py`:

- `outfit` — `shades`, `redshades`, `helmet` (EVA suit + bubble + life-support pack),
  `beanie` (+ knitted jumper), `rainhat` (+ slicker), `partyhat`, `chef` (toque +
  gingham apron), `cap` (worn backwards)
- `holding` — `mug` (steaming diner mug), `beer`, `marshmallow`, `ball`, `spatula`,
  `treats` (bowl of biscuits + spilled bones)
- `markings` — `collie`
- `name` — bone tag on the collar

Settings live in `SETTINGS` in `web/lib/dogs.ts`: beach, mountains, park, night camp,
rainy day, moon. Each picks its own outfit and prop, so the beach gets shades and a beer
and the moon gets helmets — and no beer, because a pint inside a sealed helmet is a bad
look.

## Roadmap — what reference art would be most useful

Ordered by how much each would improve the videos. Everything here is currently missing.

### Settings (10)

Six are **built and live** — drawn from code, no art needed, no cost. The remaining four
are still open.

| # | Setting | Status |
|---|---|---|
| 1 | **Living room / couch** | ✅ Built. Couch, lamp with light pool, framed paw art, book shelf, rug. Dogs hold mugs. |
| 2 | **Kitchen** | ✅ Built. Fridge with magnets, window, counter run, shelf. Chef outfit + spatula. |
| 3 | **Car interior** | ✅ Built. Windscreen onto a road with a receding centre line, dashboard with gauges, steering wheel, rear-view mirror, A-pillars. Caps on. |
| 4 | **Office / desk** | ✅ Built. Desk cutting across the frame, monitor, window, shelf, framed bone. Mugs. |
| 5 | **Snowy street** | ✅ Built. Skyline, snow drifts, falling snow. Beanies + mugs. |
| 6 | **Rooftop at sunset** | ✅ Built. Lit skyline, string lights, sunset sky. Beers. |
| 7 | **Back garden / porch** | Open. Fence, grass, a ball. Cheaper than the park and reads as home. |
| 8 | **Diner booth** | Open. Table between them, mugs, menu. Naturally seats two facing each other. |
| 9 | **Vet waiting room** | Open. Inherently funny; Woofy's dread is the joke. |
| 10 | **Pet shop aisle** | Open. Shelves of toys and treats. Lots of prop surface. |

Settings need **no reference art** — they are toolkit primitives. The characters are the
only thing that needs drawn artwork; see [`SPRITES.md`](SPRITES.md).

A setting may declare a `foreground` as well as a `backdrop`: calls drawn *after* the
characters. The car dashboard and the office desk both need it, or the dogs end up welded
to the bonnet and floating in an empty room respectively.

### Props and outfits (10)

| # | Prop / outfit | Where it is used |
|---|---|---|
| 11 | **Slogan mug art** | WOOF FUEL / PAW-SITIVE VIBES / BEST BOYS EVER — currently the mug is blank |
| 12 | **Wooden sign board** | BE KIND BE HAPPY BE YOU — the reference uses these as scene furniture |
| 13 | **Bone-shaped banner** | "LIFE IS BETTER WITH PAWS & DAD JOKES" — outro card |
| 14 | **Plate of cookies** | Table dressing for couch and diner |
| 15 | **Steering wheel + seatbelt** | Needed before the car setting works |
| 16 | **Newspaper / phone** | The classic "reading, not listening" straight-man beat |
| 17 | **Party kit** | Balloons, cake, banner. Birthday episodes |
| 18 | **Winter kit** | Scarf, mittens, earmuffs |
| 19 | **Superhero cape + mask** | Costume episodes; very shareable |
| 20 | **Fetch kit** | Frisbee, stick, tennis ball with motion arcs |

For each, the most useful reference is a **clean front view on a plain background**, since
everything is redrawn as vector primitives rather than traced — what matters is the
silhouette, the two or three colours, and the one detail that makes it read at thumbnail
size.
