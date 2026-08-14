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

One per file. Keep the first paragraph identical every time — that is what holds the
character steady across the set.

> **Goofy, base:** A friendly cartoon golden retriever puppy sitting upright, three-quarter
> view facing right, warm golden-tan fluffy fur, cream muzzle and chest, big dark round
> eyes with bright catchlights, soft rounded ears, wearing a blue collar with a small
> plain bone-shaped tag with NO writing on it. Children's picture-book illustration style,
> soft shading, clean bold outlines. Full body including both front paws. Centred on a
> completely flat plain mid-grey background, no shadow, no scenery, no text anywhere.
> **[EXPRESSION]**

> **Woofy, base:** A friendly cartoon border collie puppy sitting upright, three-quarter
> view facing right, fluffy near-black fur with a white blaze down the face, white muzzle,
> white chest and white front paws, big dark round eyes with bright catchlights, soft
> floppy ears, wearing a red collar with a small plain bone-shaped tag with NO writing on
> it. Children's picture-book illustration style, soft shading, clean bold outlines. Full
> body including both front paws. Centred on a completely flat plain mid-grey background,
> no shadow, no scenery, no text anywhere. **[EXPRESSION]**

Swap `[EXPRESSION]` for each of the four:

| File | `[EXPRESSION]` |
|---|---|
| `idle` | Mouth closed in a gentle smile, calm and attentive, listening. |
| `talk` | Mouth open mid-speech with the tongue visible, eyebrows up, clearly talking. |
| `laugh` | Mouth open wide laughing, eyes squeezed shut into happy arcs, head tilted back slightly. |
| `smug` | Mouth closed, one eyebrow raised, half-lidded knowing look, unimpressed. |

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

All three branches are verified. **No sprite art is committed**, so every episode
currently takes the third branch and renders exactly as before. Drop
`assets/sprites/goofy/talk.png` in and that dog starts using it on the next render — no
code change, no redeploy of the engine.

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
