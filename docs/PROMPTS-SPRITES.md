# Sprite prompts — copy and paste

Eight complete prompts, one per file. Nothing to assemble: each fenced block is the whole
prompt.

Settings: **1:1 square**, flat background colour **`#8C8C8C`**, highest quality tier your
tool offers, a stylised-illustration model rather than a photoreal one.

Two art-direction choices are deliberate and should not be 'improved':

- **Lighting is soft and near-symmetric, not dramatic.** Sprites are mirrored in code for the
  left-hand character, so a strong key from one side would light the two dogs from opposite
  directions in the same shot.
- **The background is flat and the character casts no shadow.** `scripts/cutout.py` keys the
  background out; a rendered environment cannot be removed, and glow or haze bleeds a halo
  into the cutout edge. The scene draws its own contact shadow.

Everything before `POSE AND EXPRESSION` is identical across a dog's four files on purpose —
that is what stops the character drifting between expressions. Do not reword it.

After saving each image:

```bash
python3 scripts/cutout.py ~/Downloads/<saved>.png assets/sprites/<dog>/<state>.png
```

## `assets/sprites/goofy/idle.png`

```text
MASTER SHOT — CHARACTER SPRITE PLATE. A cartoon golden retriever puppy. Single subject, absolutely alone in frame. Full-body three-quarter view, body angled roughly 30 degrees away from camera and facing to the RIGHT of frame, head turned slightly back toward camera so both eyes and the full muzzle read clearly. Sitting upright on his haunches, hind legs folded, both front legs straight and planted, weight settled, spine relaxed with a gentle S-curve through the neck. Framed head-to-paw with an even margin on all sides, nothing cropped, nothing touching the frame edge. Eye level with the character, lens equivalent 85mm so the proportions stay honest with no wide-angle distortion of the snout.

CHARACTER DESIGN. Built for animation appeal: a large rounded cranium, a short soft snout, a compact chest and stubby well-padded limbs, generous head-to-body ratio. Silhouette is the priority — ears, muzzle, chest ruff, tail and paws must all read as distinct shapes even when the figure is reduced to a solid black shape at thumbnail size. Anatomy correct for the breed underneath the stylisation: real shoulder and hip placement, four toes per paw, a tail that grows out of the spine rather than being pasted on. Coat is a warm honey-gold, deepening to a richer amber along the back and the tops of the ears, lightening to a pale cream on the muzzle, throat, chest ruff and the fronts of all four paws. Long soft floppy ears hanging beside the head with lightly feathered edges, and a plumed upward-curving tail.

FUR AND MATERIAL. Fur rendered as grouped, directional clumps that follow the body's form, not as noise or as a flat vector fill — a soft feathered outline where the coat meets the background, longer feathering at the chest ruff, the backs of the legs and the underside of the tail, shorter and tighter over the skull and muzzle. Subtle two-tone shading within the coat: a slightly warmer tone where light grazes the top planes, a cooler deeper tone in the undercarriage and behind the front legs. Wet-looking nose leather with a soft specular highlight. Faintly visible whisker dots on the muzzle.

FACE AND EYES. Large round dark-brown eyes with a full construction: dark iris ring, a warmer iris interior, a defined pupil, one crisp primary catchlight at the upper outer edge of each eye and a much fainter secondary bounce catchlight at the lower inner edge. Eyes symmetrical, both fully visible, sitting on the same eyeline, with soft lids and a suggestion of brow above each so expression is readable. Small rounded nose with a defined bridge running up between the eyes. Mouth line drawn with a confident tapered stroke.

WARDROBE. A plain royal-blue fabric collar with a small blank bone-shaped metal tag hanging from a tiny ring at the front. The tag is COMPLETELY BLANK — a plain smooth bone shape carrying no writing, no letters, no numbers, no engraving, no logo of any kind. Collar sits naturally in the neck fur with the coat overlapping its top edge, not floating on the surface.

LIGHTING. Soft, even, near-frontal key with broad diffusion and a gentle fill from both sides, deliberately balanced so the character is lit almost symmetrically and neither side falls into heavy shadow. A faint warm ambient wrap around the silhouette. Contact shadow must NOT be drawn — the character sits on nothing and casts nothing.

RENDER STYLE. Premium children's picture-book and feature-animation character art: clean confident tapered linework, soft cel shading with two or three tonal steps plus a gentle gradient in the largest forms, rich saturated but natural colour, high-appeal expression acting. Crisp and fully in focus across the whole figure — no depth of field, no motion blur, no bloom, no lens flare, no film grain, no vignette. High resolution, sharp clean edges suitable for cutting out.

BACKGROUND. A completely flat, uniform, solid mid-grey field filling the entire frame, exactly the same value and hue in every corner. No gradient, no vignette, no texture, no pattern, no floor, no horizon line, no environment, no atmospheric haze, no glow spill around the character.

NEGATIVE. No text, no watermark, no signature, no logo, no border or frame, no second animal, no human, no duplicate figure, no reflection, no props, no furniture, no ground plane, no cast shadow, no photorealism, no uncanny realistic dog photograph, no extra limbs, no malformed paws, no cropped ears or paws.

POSE AND EXPRESSION: Calm and attentive, listening to someone just off frame to the right. Mouth closed in a soft contented smile with the corners gently lifted. Eyes fully open, warm and steady, pupils directed slightly toward the right of frame. Brows neutral and relaxed. Ears hanging loose. Head level, chin slightly raised. Body settled and still — the quiet beat between lines.
```

## `assets/sprites/goofy/talk.png`

```text
MASTER SHOT — CHARACTER SPRITE PLATE. A cartoon golden retriever puppy. Single subject, absolutely alone in frame. Full-body three-quarter view, body angled roughly 30 degrees away from camera and facing to the RIGHT of frame, head turned slightly back toward camera so both eyes and the full muzzle read clearly. Sitting upright on his haunches, hind legs folded, both front legs straight and planted, weight settled, spine relaxed with a gentle S-curve through the neck. Framed head-to-paw with an even margin on all sides, nothing cropped, nothing touching the frame edge. Eye level with the character, lens equivalent 85mm so the proportions stay honest with no wide-angle distortion of the snout.

CHARACTER DESIGN. Built for animation appeal: a large rounded cranium, a short soft snout, a compact chest and stubby well-padded limbs, generous head-to-body ratio. Silhouette is the priority — ears, muzzle, chest ruff, tail and paws must all read as distinct shapes even when the figure is reduced to a solid black shape at thumbnail size. Anatomy correct for the breed underneath the stylisation: real shoulder and hip placement, four toes per paw, a tail that grows out of the spine rather than being pasted on. Coat is a warm honey-gold, deepening to a richer amber along the back and the tops of the ears, lightening to a pale cream on the muzzle, throat, chest ruff and the fronts of all four paws. Long soft floppy ears hanging beside the head with lightly feathered edges, and a plumed upward-curving tail.

FUR AND MATERIAL. Fur rendered as grouped, directional clumps that follow the body's form, not as noise or as a flat vector fill — a soft feathered outline where the coat meets the background, longer feathering at the chest ruff, the backs of the legs and the underside of the tail, shorter and tighter over the skull and muzzle. Subtle two-tone shading within the coat: a slightly warmer tone where light grazes the top planes, a cooler deeper tone in the undercarriage and behind the front legs. Wet-looking nose leather with a soft specular highlight. Faintly visible whisker dots on the muzzle.

FACE AND EYES. Large round dark-brown eyes with a full construction: dark iris ring, a warmer iris interior, a defined pupil, one crisp primary catchlight at the upper outer edge of each eye and a much fainter secondary bounce catchlight at the lower inner edge. Eyes symmetrical, both fully visible, sitting on the same eyeline, with soft lids and a suggestion of brow above each so expression is readable. Small rounded nose with a defined bridge running up between the eyes. Mouth line drawn with a confident tapered stroke.

WARDROBE. A plain royal-blue fabric collar with a small blank bone-shaped metal tag hanging from a tiny ring at the front. The tag is COMPLETELY BLANK — a plain smooth bone shape carrying no writing, no letters, no numbers, no engraving, no logo of any kind. Collar sits naturally in the neck fur with the coat overlapping its top edge, not floating on the surface.

LIGHTING. Soft, even, near-frontal key with broad diffusion and a gentle fill from both sides, deliberately balanced so the character is lit almost symmetrically and neither side falls into heavy shadow. A faint warm ambient wrap around the silhouette. Contact shadow must NOT be drawn — the character sits on nothing and casts nothing.

RENDER STYLE. Premium children's picture-book and feature-animation character art: clean confident tapered linework, soft cel shading with two or three tonal steps plus a gentle gradient in the largest forms, rich saturated but natural colour, high-appeal expression acting. Crisp and fully in focus across the whole figure — no depth of field, no motion blur, no bloom, no lens flare, no film grain, no vignette. High resolution, sharp clean edges suitable for cutting out.

BACKGROUND. A completely flat, uniform, solid mid-grey field filling the entire frame, exactly the same value and hue in every corner. No gradient, no vignette, no texture, no pattern, no floor, no horizon line, no environment, no atmospheric haze, no glow spill around the character.

NEGATIVE. No text, no watermark, no signature, no logo, no border or frame, no second animal, no human, no duplicate figure, no reflection, no props, no furniture, no ground plane, no cast shadow, no photorealism, no uncanny realistic dog photograph, no extra limbs, no malformed paws, no cropped ears or paws.

POSE AND EXPRESSION: Mid-sentence, animated and engaged. Mouth open with the lower jaw dropped in a clear speech shape, the soft pink tongue visible resting inside the lower jaw and a hint of the upper teeth showing. Brows raised high and slightly asymmetric, eyes wide, bright and lively. Ears lifted a little at the base with the energy of talking. Head tilted forward and turned toward the listener, chest leaning in slightly. Caught in the middle of a word, not posing.
```

## `assets/sprites/goofy/laugh.png`

```text
MASTER SHOT — CHARACTER SPRITE PLATE. A cartoon golden retriever puppy. Single subject, absolutely alone in frame. Full-body three-quarter view, body angled roughly 30 degrees away from camera and facing to the RIGHT of frame, head turned slightly back toward camera so both eyes and the full muzzle read clearly. Sitting upright on his haunches, hind legs folded, both front legs straight and planted, weight settled, spine relaxed with a gentle S-curve through the neck. Framed head-to-paw with an even margin on all sides, nothing cropped, nothing touching the frame edge. Eye level with the character, lens equivalent 85mm so the proportions stay honest with no wide-angle distortion of the snout.

CHARACTER DESIGN. Built for animation appeal: a large rounded cranium, a short soft snout, a compact chest and stubby well-padded limbs, generous head-to-body ratio. Silhouette is the priority — ears, muzzle, chest ruff, tail and paws must all read as distinct shapes even when the figure is reduced to a solid black shape at thumbnail size. Anatomy correct for the breed underneath the stylisation: real shoulder and hip placement, four toes per paw, a tail that grows out of the spine rather than being pasted on. Coat is a warm honey-gold, deepening to a richer amber along the back and the tops of the ears, lightening to a pale cream on the muzzle, throat, chest ruff and the fronts of all four paws. Long soft floppy ears hanging beside the head with lightly feathered edges, and a plumed upward-curving tail.

FUR AND MATERIAL. Fur rendered as grouped, directional clumps that follow the body's form, not as noise or as a flat vector fill — a soft feathered outline where the coat meets the background, longer feathering at the chest ruff, the backs of the legs and the underside of the tail, shorter and tighter over the skull and muzzle. Subtle two-tone shading within the coat: a slightly warmer tone where light grazes the top planes, a cooler deeper tone in the undercarriage and behind the front legs. Wet-looking nose leather with a soft specular highlight. Faintly visible whisker dots on the muzzle.

FACE AND EYES. Large round dark-brown eyes with a full construction: dark iris ring, a warmer iris interior, a defined pupil, one crisp primary catchlight at the upper outer edge of each eye and a much fainter secondary bounce catchlight at the lower inner edge. Eyes symmetrical, both fully visible, sitting on the same eyeline, with soft lids and a suggestion of brow above each so expression is readable. Small rounded nose with a defined bridge running up between the eyes. Mouth line drawn with a confident tapered stroke.

WARDROBE. A plain royal-blue fabric collar with a small blank bone-shaped metal tag hanging from a tiny ring at the front. The tag is COMPLETELY BLANK — a plain smooth bone shape carrying no writing, no letters, no numbers, no engraving, no logo of any kind. Collar sits naturally in the neck fur with the coat overlapping its top edge, not floating on the surface.

LIGHTING. Soft, even, near-frontal key with broad diffusion and a gentle fill from both sides, deliberately balanced so the character is lit almost symmetrically and neither side falls into heavy shadow. A faint warm ambient wrap around the silhouette. Contact shadow must NOT be drawn — the character sits on nothing and casts nothing.

RENDER STYLE. Premium children's picture-book and feature-animation character art: clean confident tapered linework, soft cel shading with two or three tonal steps plus a gentle gradient in the largest forms, rich saturated but natural colour, high-appeal expression acting. Crisp and fully in focus across the whole figure — no depth of field, no motion blur, no bloom, no lens flare, no film grain, no vignette. High resolution, sharp clean edges suitable for cutting out.

BACKGROUND. A completely flat, uniform, solid mid-grey field filling the entire frame, exactly the same value and hue in every corner. No gradient, no vignette, no texture, no pattern, no floor, no horizon line, no environment, no atmospheric haze, no glow spill around the character.

NEGATIVE. No text, no watermark, no signature, no logo, no border or frame, no second animal, no human, no duplicate figure, no reflection, no props, no furniture, no ground plane, no cast shadow, no photorealism, no uncanny realistic dog photograph, no extra limbs, no malformed paws, no cropped ears or paws.

POSE AND EXPRESSION: Helpless delighted laughter at his own joke. Mouth open wide and rounded in a full laugh with the tongue clearly showing and the throat visible, cheeks pushed up. Both eyes squeezed shut into two happy upward-curving arcs, crescents rather than circles. Brows raised high. Ears lifted and flung back. Head tilted back and slightly to one side, shoulders raised and body rocking back with the force of it. Pure uncomplicated joy.
```

## `assets/sprites/goofy/smug.png`

```text
MASTER SHOT — CHARACTER SPRITE PLATE. A cartoon golden retriever puppy. Single subject, absolutely alone in frame. Full-body three-quarter view, body angled roughly 30 degrees away from camera and facing to the RIGHT of frame, head turned slightly back toward camera so both eyes and the full muzzle read clearly. Sitting upright on his haunches, hind legs folded, both front legs straight and planted, weight settled, spine relaxed with a gentle S-curve through the neck. Framed head-to-paw with an even margin on all sides, nothing cropped, nothing touching the frame edge. Eye level with the character, lens equivalent 85mm so the proportions stay honest with no wide-angle distortion of the snout.

CHARACTER DESIGN. Built for animation appeal: a large rounded cranium, a short soft snout, a compact chest and stubby well-padded limbs, generous head-to-body ratio. Silhouette is the priority — ears, muzzle, chest ruff, tail and paws must all read as distinct shapes even when the figure is reduced to a solid black shape at thumbnail size. Anatomy correct for the breed underneath the stylisation: real shoulder and hip placement, four toes per paw, a tail that grows out of the spine rather than being pasted on. Coat is a warm honey-gold, deepening to a richer amber along the back and the tops of the ears, lightening to a pale cream on the muzzle, throat, chest ruff and the fronts of all four paws. Long soft floppy ears hanging beside the head with lightly feathered edges, and a plumed upward-curving tail.

FUR AND MATERIAL. Fur rendered as grouped, directional clumps that follow the body's form, not as noise or as a flat vector fill — a soft feathered outline where the coat meets the background, longer feathering at the chest ruff, the backs of the legs and the underside of the tail, shorter and tighter over the skull and muzzle. Subtle two-tone shading within the coat: a slightly warmer tone where light grazes the top planes, a cooler deeper tone in the undercarriage and behind the front legs. Wet-looking nose leather with a soft specular highlight. Faintly visible whisker dots on the muzzle.

FACE AND EYES. Large round dark-brown eyes with a full construction: dark iris ring, a warmer iris interior, a defined pupil, one crisp primary catchlight at the upper outer edge of each eye and a much fainter secondary bounce catchlight at the lower inner edge. Eyes symmetrical, both fully visible, sitting on the same eyeline, with soft lids and a suggestion of brow above each so expression is readable. Small rounded nose with a defined bridge running up between the eyes. Mouth line drawn with a confident tapered stroke.

WARDROBE. A plain royal-blue fabric collar with a small blank bone-shaped metal tag hanging from a tiny ring at the front. The tag is COMPLETELY BLANK — a plain smooth bone shape carrying no writing, no letters, no numbers, no engraving, no logo of any kind. Collar sits naturally in the neck fur with the coat overlapping its top edge, not floating on the surface.

LIGHTING. Soft, even, near-frontal key with broad diffusion and a gentle fill from both sides, deliberately balanced so the character is lit almost symmetrically and neither side falls into heavy shadow. A faint warm ambient wrap around the silhouette. Contact shadow must NOT be drawn — the character sits on nothing and casts nothing.

RENDER STYLE. Premium children's picture-book and feature-animation character art: clean confident tapered linework, soft cel shading with two or three tonal steps plus a gentle gradient in the largest forms, rich saturated but natural colour, high-appeal expression acting. Crisp and fully in focus across the whole figure — no depth of field, no motion blur, no bloom, no lens flare, no film grain, no vignette. High resolution, sharp clean edges suitable for cutting out.

BACKGROUND. A completely flat, uniform, solid mid-grey field filling the entire frame, exactly the same value and hue in every corner. No gradient, no vignette, no texture, no pattern, no floor, no horizon line, no environment, no atmospheric haze, no glow spill around the character.

NEGATIVE. No text, no watermark, no signature, no logo, no border or frame, no second animal, no human, no duplicate figure, no reflection, no props, no furniture, no ground plane, no cast shadow, no photorealism, no uncanny realistic dog photograph, no extra limbs, no malformed paws, no cropped ears or paws.

POSE AND EXPRESSION: Thoroughly unimpressed and enjoying it. Mouth closed in a small crooked knowing smirk, one corner pulled up higher than the other. Eyes half-lidded and heavy, sliding sideways in a deadpan look toward the right of frame rather than at camera. One brow raised distinctly higher than the other. Ears low and relaxed. Head level with the chin dipped very slightly, utterly still. Deadpan comic timing — the straight man waiting for the punchline to end.
```

## `assets/sprites/woofy/idle.png`

```text
MASTER SHOT — CHARACTER SPRITE PLATE. A cartoon border collie puppy. Single subject, absolutely alone in frame. Full-body three-quarter view, body angled roughly 30 degrees away from camera and facing to the RIGHT of frame, head turned slightly back toward camera so both eyes and the full muzzle read clearly. Sitting upright on his haunches, hind legs folded, both front legs straight and planted, weight settled, spine relaxed with a gentle S-curve through the neck. Framed head-to-paw with an even margin on all sides, nothing cropped, nothing touching the frame edge. Eye level with the character, lens equivalent 85mm so the proportions stay honest with no wide-angle distortion of the snout.

CHARACTER DESIGN. Built for animation appeal: a large rounded cranium, a short soft snout, a compact chest and stubby well-padded limbs, generous head-to-body ratio. Silhouette is the priority — ears, muzzle, chest ruff, tail and paws must all read as distinct shapes even when the figure is reduced to a solid black shape at thumbnail size. Anatomy correct for the breed underneath the stylisation: real shoulder and hip placement, four toes per paw, a tail that grows out of the spine rather than being pasted on. Coat is a deep near-black with a faint cool blue sheen where light grazes it, contrasted against crisp bright white markings. Classic collie markings: a clean white blaze running up the centre of the muzzle and between the eyes onto the forehead, a white muzzle and chin, a broad white chest bib, white front paws and socks, and a white tip to the tail. Ears soft and floppy, black, with lightly feathered edges.

FUR AND MATERIAL. Fur rendered as grouped, directional clumps that follow the body's form, not as noise or as a flat vector fill — a soft feathered outline where the coat meets the background, longer feathering at the chest ruff, the backs of the legs and the underside of the tail, shorter and tighter over the skull and muzzle. Subtle two-tone shading within the coat: a slightly warmer tone where light grazes the top planes, a cooler deeper tone in the undercarriage and behind the front legs. Wet-looking nose leather with a soft specular highlight. Faintly visible whisker dots on the muzzle.

FACE AND EYES. Large round dark-brown eyes with a full construction: dark iris ring, a warmer iris interior, a defined pupil, one crisp primary catchlight at the upper outer edge of each eye and a much fainter secondary bounce catchlight at the lower inner edge. Eyes symmetrical, both fully visible, sitting on the same eyeline, with soft lids and a suggestion of brow above each so expression is readable. Small rounded nose with a defined bridge running up between the eyes. Mouth line drawn with a confident tapered stroke.

WARDROBE. A plain red fabric collar with a small blank bone-shaped metal tag hanging from a tiny ring at the front. The tag is COMPLETELY BLANK — a plain smooth bone shape carrying no writing, no letters, no numbers, no engraving, no logo of any kind. Collar sits naturally in the neck fur with the coat overlapping its top edge, not floating on the surface.

LIGHTING. Soft, even, near-frontal key with broad diffusion and a gentle fill from both sides, deliberately balanced so the character is lit almost symmetrically and neither side falls into heavy shadow. A faint warm ambient wrap around the silhouette. Contact shadow must NOT be drawn — the character sits on nothing and casts nothing.

RENDER STYLE. Premium children's picture-book and feature-animation character art: clean confident tapered linework, soft cel shading with two or three tonal steps plus a gentle gradient in the largest forms, rich saturated but natural colour, high-appeal expression acting. Crisp and fully in focus across the whole figure — no depth of field, no motion blur, no bloom, no lens flare, no film grain, no vignette. High resolution, sharp clean edges suitable for cutting out.

BACKGROUND. A completely flat, uniform, solid mid-grey field filling the entire frame, exactly the same value and hue in every corner. No gradient, no vignette, no texture, no pattern, no floor, no horizon line, no environment, no atmospheric haze, no glow spill around the character.

NEGATIVE. No text, no watermark, no signature, no logo, no border or frame, no second animal, no human, no duplicate figure, no reflection, no props, no furniture, no ground plane, no cast shadow, no photorealism, no uncanny realistic dog photograph, no extra limbs, no malformed paws, no cropped ears or paws.

POSE AND EXPRESSION: Calm and attentive, listening to someone just off frame to the right. Mouth closed in a soft contented smile with the corners gently lifted. Eyes fully open, warm and steady, pupils directed slightly toward the right of frame. Brows neutral and relaxed. Ears hanging loose. Head level, chin slightly raised. Body settled and still — the quiet beat between lines.
```

## `assets/sprites/woofy/talk.png`

```text
MASTER SHOT — CHARACTER SPRITE PLATE. A cartoon border collie puppy. Single subject, absolutely alone in frame. Full-body three-quarter view, body angled roughly 30 degrees away from camera and facing to the RIGHT of frame, head turned slightly back toward camera so both eyes and the full muzzle read clearly. Sitting upright on his haunches, hind legs folded, both front legs straight and planted, weight settled, spine relaxed with a gentle S-curve through the neck. Framed head-to-paw with an even margin on all sides, nothing cropped, nothing touching the frame edge. Eye level with the character, lens equivalent 85mm so the proportions stay honest with no wide-angle distortion of the snout.

CHARACTER DESIGN. Built for animation appeal: a large rounded cranium, a short soft snout, a compact chest and stubby well-padded limbs, generous head-to-body ratio. Silhouette is the priority — ears, muzzle, chest ruff, tail and paws must all read as distinct shapes even when the figure is reduced to a solid black shape at thumbnail size. Anatomy correct for the breed underneath the stylisation: real shoulder and hip placement, four toes per paw, a tail that grows out of the spine rather than being pasted on. Coat is a deep near-black with a faint cool blue sheen where light grazes it, contrasted against crisp bright white markings. Classic collie markings: a clean white blaze running up the centre of the muzzle and between the eyes onto the forehead, a white muzzle and chin, a broad white chest bib, white front paws and socks, and a white tip to the tail. Ears soft and floppy, black, with lightly feathered edges.

FUR AND MATERIAL. Fur rendered as grouped, directional clumps that follow the body's form, not as noise or as a flat vector fill — a soft feathered outline where the coat meets the background, longer feathering at the chest ruff, the backs of the legs and the underside of the tail, shorter and tighter over the skull and muzzle. Subtle two-tone shading within the coat: a slightly warmer tone where light grazes the top planes, a cooler deeper tone in the undercarriage and behind the front legs. Wet-looking nose leather with a soft specular highlight. Faintly visible whisker dots on the muzzle.

FACE AND EYES. Large round dark-brown eyes with a full construction: dark iris ring, a warmer iris interior, a defined pupil, one crisp primary catchlight at the upper outer edge of each eye and a much fainter secondary bounce catchlight at the lower inner edge. Eyes symmetrical, both fully visible, sitting on the same eyeline, with soft lids and a suggestion of brow above each so expression is readable. Small rounded nose with a defined bridge running up between the eyes. Mouth line drawn with a confident tapered stroke.

WARDROBE. A plain red fabric collar with a small blank bone-shaped metal tag hanging from a tiny ring at the front. The tag is COMPLETELY BLANK — a plain smooth bone shape carrying no writing, no letters, no numbers, no engraving, no logo of any kind. Collar sits naturally in the neck fur with the coat overlapping its top edge, not floating on the surface.

LIGHTING. Soft, even, near-frontal key with broad diffusion and a gentle fill from both sides, deliberately balanced so the character is lit almost symmetrically and neither side falls into heavy shadow. A faint warm ambient wrap around the silhouette. Contact shadow must NOT be drawn — the character sits on nothing and casts nothing.

RENDER STYLE. Premium children's picture-book and feature-animation character art: clean confident tapered linework, soft cel shading with two or three tonal steps plus a gentle gradient in the largest forms, rich saturated but natural colour, high-appeal expression acting. Crisp and fully in focus across the whole figure — no depth of field, no motion blur, no bloom, no lens flare, no film grain, no vignette. High resolution, sharp clean edges suitable for cutting out.

BACKGROUND. A completely flat, uniform, solid mid-grey field filling the entire frame, exactly the same value and hue in every corner. No gradient, no vignette, no texture, no pattern, no floor, no horizon line, no environment, no atmospheric haze, no glow spill around the character.

NEGATIVE. No text, no watermark, no signature, no logo, no border or frame, no second animal, no human, no duplicate figure, no reflection, no props, no furniture, no ground plane, no cast shadow, no photorealism, no uncanny realistic dog photograph, no extra limbs, no malformed paws, no cropped ears or paws.

POSE AND EXPRESSION: Mid-sentence, animated and engaged. Mouth open with the lower jaw dropped in a clear speech shape, the soft pink tongue visible resting inside the lower jaw and a hint of the upper teeth showing. Brows raised high and slightly asymmetric, eyes wide, bright and lively. Ears lifted a little at the base with the energy of talking. Head tilted forward and turned toward the listener, chest leaning in slightly. Caught in the middle of a word, not posing.
```

## `assets/sprites/woofy/laugh.png`

```text
MASTER SHOT — CHARACTER SPRITE PLATE. A cartoon border collie puppy. Single subject, absolutely alone in frame. Full-body three-quarter view, body angled roughly 30 degrees away from camera and facing to the RIGHT of frame, head turned slightly back toward camera so both eyes and the full muzzle read clearly. Sitting upright on his haunches, hind legs folded, both front legs straight and planted, weight settled, spine relaxed with a gentle S-curve through the neck. Framed head-to-paw with an even margin on all sides, nothing cropped, nothing touching the frame edge. Eye level with the character, lens equivalent 85mm so the proportions stay honest with no wide-angle distortion of the snout.

CHARACTER DESIGN. Built for animation appeal: a large rounded cranium, a short soft snout, a compact chest and stubby well-padded limbs, generous head-to-body ratio. Silhouette is the priority — ears, muzzle, chest ruff, tail and paws must all read as distinct shapes even when the figure is reduced to a solid black shape at thumbnail size. Anatomy correct for the breed underneath the stylisation: real shoulder and hip placement, four toes per paw, a tail that grows out of the spine rather than being pasted on. Coat is a deep near-black with a faint cool blue sheen where light grazes it, contrasted against crisp bright white markings. Classic collie markings: a clean white blaze running up the centre of the muzzle and between the eyes onto the forehead, a white muzzle and chin, a broad white chest bib, white front paws and socks, and a white tip to the tail. Ears soft and floppy, black, with lightly feathered edges.

FUR AND MATERIAL. Fur rendered as grouped, directional clumps that follow the body's form, not as noise or as a flat vector fill — a soft feathered outline where the coat meets the background, longer feathering at the chest ruff, the backs of the legs and the underside of the tail, shorter and tighter over the skull and muzzle. Subtle two-tone shading within the coat: a slightly warmer tone where light grazes the top planes, a cooler deeper tone in the undercarriage and behind the front legs. Wet-looking nose leather with a soft specular highlight. Faintly visible whisker dots on the muzzle.

FACE AND EYES. Large round dark-brown eyes with a full construction: dark iris ring, a warmer iris interior, a defined pupil, one crisp primary catchlight at the upper outer edge of each eye and a much fainter secondary bounce catchlight at the lower inner edge. Eyes symmetrical, both fully visible, sitting on the same eyeline, with soft lids and a suggestion of brow above each so expression is readable. Small rounded nose with a defined bridge running up between the eyes. Mouth line drawn with a confident tapered stroke.

WARDROBE. A plain red fabric collar with a small blank bone-shaped metal tag hanging from a tiny ring at the front. The tag is COMPLETELY BLANK — a plain smooth bone shape carrying no writing, no letters, no numbers, no engraving, no logo of any kind. Collar sits naturally in the neck fur with the coat overlapping its top edge, not floating on the surface.

LIGHTING. Soft, even, near-frontal key with broad diffusion and a gentle fill from both sides, deliberately balanced so the character is lit almost symmetrically and neither side falls into heavy shadow. A faint warm ambient wrap around the silhouette. Contact shadow must NOT be drawn — the character sits on nothing and casts nothing.

RENDER STYLE. Premium children's picture-book and feature-animation character art: clean confident tapered linework, soft cel shading with two or three tonal steps plus a gentle gradient in the largest forms, rich saturated but natural colour, high-appeal expression acting. Crisp and fully in focus across the whole figure — no depth of field, no motion blur, no bloom, no lens flare, no film grain, no vignette. High resolution, sharp clean edges suitable for cutting out.

BACKGROUND. A completely flat, uniform, solid mid-grey field filling the entire frame, exactly the same value and hue in every corner. No gradient, no vignette, no texture, no pattern, no floor, no horizon line, no environment, no atmospheric haze, no glow spill around the character.

NEGATIVE. No text, no watermark, no signature, no logo, no border or frame, no second animal, no human, no duplicate figure, no reflection, no props, no furniture, no ground plane, no cast shadow, no photorealism, no uncanny realistic dog photograph, no extra limbs, no malformed paws, no cropped ears or paws.

POSE AND EXPRESSION: Helpless delighted laughter at his own joke. Mouth open wide and rounded in a full laugh with the tongue clearly showing and the throat visible, cheeks pushed up. Both eyes squeezed shut into two happy upward-curving arcs, crescents rather than circles. Brows raised high. Ears lifted and flung back. Head tilted back and slightly to one side, shoulders raised and body rocking back with the force of it. Pure uncomplicated joy.
```

## `assets/sprites/woofy/smug.png`

```text
MASTER SHOT — CHARACTER SPRITE PLATE. A cartoon border collie puppy. Single subject, absolutely alone in frame. Full-body three-quarter view, body angled roughly 30 degrees away from camera and facing to the RIGHT of frame, head turned slightly back toward camera so both eyes and the full muzzle read clearly. Sitting upright on his haunches, hind legs folded, both front legs straight and planted, weight settled, spine relaxed with a gentle S-curve through the neck. Framed head-to-paw with an even margin on all sides, nothing cropped, nothing touching the frame edge. Eye level with the character, lens equivalent 85mm so the proportions stay honest with no wide-angle distortion of the snout.

CHARACTER DESIGN. Built for animation appeal: a large rounded cranium, a short soft snout, a compact chest and stubby well-padded limbs, generous head-to-body ratio. Silhouette is the priority — ears, muzzle, chest ruff, tail and paws must all read as distinct shapes even when the figure is reduced to a solid black shape at thumbnail size. Anatomy correct for the breed underneath the stylisation: real shoulder and hip placement, four toes per paw, a tail that grows out of the spine rather than being pasted on. Coat is a deep near-black with a faint cool blue sheen where light grazes it, contrasted against crisp bright white markings. Classic collie markings: a clean white blaze running up the centre of the muzzle and between the eyes onto the forehead, a white muzzle and chin, a broad white chest bib, white front paws and socks, and a white tip to the tail. Ears soft and floppy, black, with lightly feathered edges.

FUR AND MATERIAL. Fur rendered as grouped, directional clumps that follow the body's form, not as noise or as a flat vector fill — a soft feathered outline where the coat meets the background, longer feathering at the chest ruff, the backs of the legs and the underside of the tail, shorter and tighter over the skull and muzzle. Subtle two-tone shading within the coat: a slightly warmer tone where light grazes the top planes, a cooler deeper tone in the undercarriage and behind the front legs. Wet-looking nose leather with a soft specular highlight. Faintly visible whisker dots on the muzzle.

FACE AND EYES. Large round dark-brown eyes with a full construction: dark iris ring, a warmer iris interior, a defined pupil, one crisp primary catchlight at the upper outer edge of each eye and a much fainter secondary bounce catchlight at the lower inner edge. Eyes symmetrical, both fully visible, sitting on the same eyeline, with soft lids and a suggestion of brow above each so expression is readable. Small rounded nose with a defined bridge running up between the eyes. Mouth line drawn with a confident tapered stroke.

WARDROBE. A plain red fabric collar with a small blank bone-shaped metal tag hanging from a tiny ring at the front. The tag is COMPLETELY BLANK — a plain smooth bone shape carrying no writing, no letters, no numbers, no engraving, no logo of any kind. Collar sits naturally in the neck fur with the coat overlapping its top edge, not floating on the surface.

LIGHTING. Soft, even, near-frontal key with broad diffusion and a gentle fill from both sides, deliberately balanced so the character is lit almost symmetrically and neither side falls into heavy shadow. A faint warm ambient wrap around the silhouette. Contact shadow must NOT be drawn — the character sits on nothing and casts nothing.

RENDER STYLE. Premium children's picture-book and feature-animation character art: clean confident tapered linework, soft cel shading with two or three tonal steps plus a gentle gradient in the largest forms, rich saturated but natural colour, high-appeal expression acting. Crisp and fully in focus across the whole figure — no depth of field, no motion blur, no bloom, no lens flare, no film grain, no vignette. High resolution, sharp clean edges suitable for cutting out.

BACKGROUND. A completely flat, uniform, solid mid-grey field filling the entire frame, exactly the same value and hue in every corner. No gradient, no vignette, no texture, no pattern, no floor, no horizon line, no environment, no atmospheric haze, no glow spill around the character.

NEGATIVE. No text, no watermark, no signature, no logo, no border or frame, no second animal, no human, no duplicate figure, no reflection, no props, no furniture, no ground plane, no cast shadow, no photorealism, no uncanny realistic dog photograph, no extra limbs, no malformed paws, no cropped ears or paws.

POSE AND EXPRESSION: Thoroughly unimpressed and enjoying it. Mouth closed in a small crooked knowing smirk, one corner pulled up higher than the other. Eyes half-lidded and heavy, sliding sideways in a deadpan look toward the right of frame rather than at camera. One brow raised distinctly higher than the other. Ears low and relaxed. Head level with the chin dipped very slightly, utterly still. Deadpan comic timing — the straight man waiting for the punchline to end.
```
