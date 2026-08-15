# Character sprites

The vector `tk.dog()` primitive draws with flat ellipses and polygons. That is fine for
the science episodes' props, but it cannot look like the painted cast reference in
[`reference/cast-goofy-woofy.png`](reference/cast-goofy-woofy.png) — no amount of tuning
the shapes gets fur, soft shading, or real muzzle structure.

So the dad-jokes leads come in as **sprites**: transparent PNGs composited onto the frame
by `tk.sprite()`. Everything around them — backdrops, bubbles, captions, end cards —
stays code-drawn.

```python
tk.sprite(img, "goofy/talk", 470, 1010, 420, facing="right")
#              name          x    y     height
```

- `x, y` is the **middle of the bottom edge**, matching how `dog()` treats its paws, so a
  sprite drops into an existing scene without moving anything else.
- `height` is in logical 1920x1080 units; the canvas is supersampled and the paste is
  scaled to match.
- Art is authored **facing right** and mirrored in code for the left-hand character.

## Two hard constraints on the art

1. **Transparent background, no shadow baked in.** The scene draws its own contact
   shadow. A sprite carrying a white or scene background will paste as a visible
   rectangle — exactly what the first pipeline test showed.
2. **No text anywhere on the sprite.** Mirroring is what halves the file count, and it
   reverses any lettering with it. The bone collar tags in the reference must therefore be
   *blank* in the art — the names get drawn over the sprite in code, the right way round.
   Same goes for slogans on mugs.

## Manifest

Minimum viable set — 8 files. Each dog sits, three-quarter view, facing right.

| File | Who | Mouth | Used for |
|---|---|---|---|
| `goofy/idle.png` | Goofy | closed, smiling | listening |
| `goofy/talk.png` | Goofy | open, tongue visible | has the line |
| `goofy/laugh.png` | Goofy | open wide, eyes squeezed shut | punchline |
| `goofy/smug.png` | Goofy | closed, one brow raised | setup |
| `woofy/idle.png` | Woofy | closed, smiling | listening |
| `woofy/talk.png` | Woofy | open, tongue visible | has the line |
| `woofy/laugh.png` | Woofy | open wide, eyes squeezed shut | punchline |
| `woofy/smug.png` | Woofy | closed, flat unimpressed stare | setup |

Costumes multiply this set, so they are deliberately deferred. Two ways to handle them
once the base set is proven, cheapest first:

- **Draw them in code over the sprite** — the existing `outfit`/`holding` code already
  produces hats, glasses, mugs and suits and could be layered on top. Cheap, flexible,
  but a flat vector hat on painted art may look pasted on.
- **Author per-costume sprites** — `goofy/space-talk.png` and so on. Looks right, but it
  is 8 more files per costume and six settings currently want one.

Decide that after seeing the base eight in a real frame.

## Making them, free

No paid service is involved. Generate the images in whatever chat image tool made the
cast reference, on a **plain flat background**, then cut them out locally:

```bash
python3 scripts/cutout.py ~/Downloads/goofy-talk.png assets/sprites/goofy/talk.png
```

`scripts/cutout.py` floods inward from the edges rather than deleting every pixel that
matches the background colour — which is what keeps Woofy's white blaze and white chest
intact instead of punching holes through them. It trims to the character and leaves a
small transparent margin. Pass `--check` to see the result without writing, and
`--thresh` to adjust tolerance if edges are eaten (lower it) or the background survives
(raise it).

Ask for a **flat mid-grey or plain white background** and no drop shadow. Gradients,
vignettes and painted scenery cannot be keyed this way; the script warns when almost
nothing was removed, which is the signal that the background was not flat enough.

### Prompts

Eight prompts. The **identity block is byte-identical** within a dog's four — that
repetition is what stops the character drifting between expressions, and drift is exactly
what would read as a jump cut when consecutive scenes swap one file for another in the
same position. Change only the sentence after `POSE AND EXPRESSION:`.

Recommended settings: square aspect ratio (1:1), flat background colour `#8C8C8C`, and a
flat-illustration model rather than a photoreal one.

#### Goofy — identity block

> A single friendly cartoon golden retriever puppy, sitting upright on his haunches, seen
> in three-quarter view facing to the RIGHT of frame. Warm golden-tan fluffy fur with
> slightly darker gold ears, a cream-coloured muzzle, cream chest and cream front paws. A
> large rounded head with a short soft snout and a big dark nose. Big round dark-brown
> eyes with bright white catchlights, set wide and friendly. Long soft floppy ears hanging
> beside the head. Wearing a plain royal-blue collar with a small blank bone-shaped tag —
> the tag is completely empty with absolutely no writing, letters or numbers on it.
> Full body visible from the tips of both ears down to both front paws, nothing cropped.
> Children's picture-book illustration style: clean confident outlines, soft cel shading,
> warm friendly proportions, slightly oversized head. Even flat lighting, no harsh
> shadows. Centred in frame with a small even margin, on a completely flat plain solid
> mid-grey background. No drop shadow, no ground, no scenery, no props, no other animals,
> no text, no watermark, no border.
> **POSE AND EXPRESSION: [see table]**

#### Woofy — identity block

> A single friendly cartoon border collie puppy, sitting upright on his haunches, seen in
> three-quarter view facing to the RIGHT of frame. Fluffy near-black fur with a crisp
> white blaze running down the centre of the face between the eyes, a white muzzle, a
> broad white chest and white front paws, and a white tip on the tail. A large rounded
> head with a short soft snout and a big dark nose. Big round dark-brown eyes with bright
> white catchlights. Soft floppy black ears hanging beside the head. Wearing a plain red
> collar with a small blank bone-shaped tag — the tag is completely empty with absolutely
> no writing, letters or numbers on it. Full body visible from the tips of both ears down
> to both front paws, nothing cropped. Children's picture-book illustration style: clean
> confident outlines, soft cel shading, warm friendly proportions, slightly oversized
> head. Even flat lighting, no harsh shadows. Centred in frame with a small even margin,
> on a completely flat plain solid mid-grey background. No drop shadow, no ground, no
> scenery, no props, no other animals, no text, no watermark, no border.
> **POSE AND EXPRESSION: [see table]**

#### The four endings

| File | `POSE AND EXPRESSION:` |
|---|---|
| `idle` | Mouth closed in a soft contented smile, eyes open and attentive, head level, ears relaxed — quietly listening to someone off to the right. |
| `talk` | Mouth open in mid-sentence with the lower jaw dropped and the pink tongue visible inside, eyebrows raised, eyes bright and wide — clearly in the middle of saying something. |
| `laugh` | Mouth open wide in a big delighted laugh, tongue showing, eyes squeezed shut into two happy upward arcs, head tilted back a little, ears lifted — helpless laughter. |
| `smug` | Mouth closed in a small crooked knowing smirk, one eyebrow raised higher than the other, eyes half-lidded and looking sideways — thoroughly unimpressed. |

Filenames: `assets/sprites/goofy/idle.png`, `.../talk.png`, `.../laugh.png`, `.../smug.png`,
then the same four under `woofy/`.

## Authoring notes

- Square-ish canvas, transparent, at least 1024px tall. The dog should fill the frame
  with a few pixels of margin; `tk.sprite()` scales by height, so consistent framing
  across the set matters more than exact dimensions.
- Keep the sitting pose and the eye line identical across a dog's four files. Anything
  that shifts between expressions will read as a jump cut, because consecutive scenes
  swap one file for another in the same position.
- Goofy: golden retriever, warm gold coat, cream muzzle and chest, blue collar with a
  blank bone tag. Woofy: border collie, near-black coat, white blaze, muzzle, chest and
  paws, red collar with a blank bone tag.

Full character definitions are in [`CAST.md`](CAST.md).

## Status

Fully wired. Episodes emit `tk.character(...)`, which resolves art most-specific first:

```
goofy/space-talk   costume art, if it has been drawn
goofy/talk         plain art, costume dropped
tk.dog(...)        vector fallback
```

**The base eight are committed and live.** Both leads render as painted artwork in every
setting; the vector `dog()` is now only a fallback for art that does not exist yet, which
in practice means costumes.

Two things were tuned once real art was in a frame, both worth knowing before adding more:

- `SPRITE_HEIGHT` is 470 logical units, not the vector dog's 360. Painted art carries a
  swept tail and spread ears inside its bounding box, so at matched heights the body reads
  noticeably smaller than the vector version did.
- The speech bubble's tail target is derived from that height. It used to be a fixed
  `640`, which was the vector dog's head top; against taller sprite art the tail dots
  landed across the speaker's face.

Two consequences of switching a dog to sprites, both by design:

- **Costumes disappear until costume art exists.** The vector `outfit`/`holding` shapes
  are positioned against the vector body's geometry and would sit wrong on painted art,
  so they are not drawn over a sprite. A sprite'd dog in the moon setting is a dog with
  no space helmet until `goofy/helmet-talk.png` exists.
- **Name tags are not drawn.** Placing them correctly needs real art to measure against;
  doing it blind would risk stamping a tag across a face. The blank tag in the art stays
  blank for now.

Because the fallback is per-file, a half-finished set degrades unevenly — Goofy in
painted art beside a vector Woofy. Add all four files for a dog before rendering.
