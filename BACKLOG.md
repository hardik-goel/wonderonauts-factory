# Episode backlog

Ideas queued for the Wonder-o-nauts. Each one is a question a six-year-old
actually asks, with a real scientific answer that can be drawn from toolkit
primitives.

Move an idea into production with:

```bash
python3 plan_season.py add <slug>
```

---

## Research template (fill this in before scripting)

```
Slug:            why-do-we-have-seasons
Question:        Why is it hot in summer and cold in winter?
Age band:        4-9
Core idea:       Earth's axis is tilted, so sunlight arrives spread out or concentrated
Misconception:   "Summer is when Earth is closer to the Sun" -- it is not; the tilt does it
Wow moment:      Shine a torch straight down, then at a slant, on the same paper
Scenes:          10  (title, question, the tilt, straight vs slanted light,
                 spread-out sunlight, orbit, opposite hemispheres, torch test,
                 bonus: the poles, outro)
New primitives:  earth_tilted(), orbit_ring(), light_cone()
Shorts scenes:   2, 5, 8
Thumbnail text:  Why do we have\nSEASONS?
Music seed:      from the slug hash (new_episode.py fills it in)
Sources checked: (2 kid-level + 1 adult-level source, note the disagreement if any)
Safety note:     the hands-on experiment must be safe unsupervised (no
                 sun-staring, no hot, sharp or electrical props)
```

Rules of thumb learned on episodes 1 and 2:

- 10 scenes, 35–55 words each, lands around 3.5–4.5 minutes. That is the sweet
  spot for this age band.
- Two "secrets" per episode, maximum. Episode 1: hidden rainbow + scattering.
- Always add a bonus wonder near the end (sunset magic) — it is the moment
  viewers repeat to a grown-up.
- Every episode ends with a question to the comments.
- Name the misconception and kill it. Episode 2 says outright that planes do not
  fly because "the air on top has further to go" -- the popular explanation is
  simply wrong, and kids deserve the real one.
- Budget one or two new toolkit primitives per episode. More than that and the
  episode is fighting the visual identity instead of extending it.

---

## Produced

| Slug | Question | Episode | Primitives it added to the toolkit |
|---|---|---|---|
| `why-is-the-sky-blue` | Why is the sky blue? | 1 | `sun`, `kid`, `rocket`, `molecule`, `zig_ray`, `prism` |
| `how-do-planes-fly` | How do planes stay up? | 2 | `plane`, `paper_plane`, `airfoil`, `wind_streaks`, `force_arrow` |

## Queued

| Slug | Question | Core idea | New primitives |
|---|---|---|---|
| `why-do-we-have-seasons` | Why is it hot then cold? | Earth's tilt, not distance | `earth_tilted`, `orbit_ring` |
| `where-does-rain-come-from` | Where does rain come from? | The water cycle | `raindrop`, `cycle_arrow` |
| `why-is-the-ocean-salty` | Why is the sea salty? | Rivers carry dissolved rock to the sea | `wave`, `salt_crystal` |
| `how-do-magnets-work` | Why do magnets stick? | Aligned magnetic domains, field lines | `magnet`, `field_line` |
| `why-do-we-need-sleep` | Why must we sleep? | Brain sorts and stores the day | `brain`, `zzz` |
| `what-are-clouds-made-of` | What are clouds made of? | Trillions of tiny water droplets | reuse `cloud`, `molecule` |
| `why-does-the-moon-change` | Why does the Moon change shape? | We see different lit halves | `moon_phase`, `orbit_ring` |
| `how-do-plants-eat-sunlight` | How do plants eat light? | Photosynthesis, simply | `leaf`, `sugar_blob` |
| `why-do-things-fall-down` | Why do things fall? | Gravity pulls everything toward Earth | `apple`, `mass_arrow` |
| `what-makes-a-rainbow` | How is a rainbow made? | Refraction + reflection in raindrops | reuse `prism`, `zig_ray` |
| `why-do-we-yawn` | Why do we yawn? | Honest answer: scientists still argue | `kid` variants |

## Parked (harder to draw honestly for this age band)

- Why is the sky dark at night? (Olbers' paradox — needs expanding-universe setup)
- What is electricity? (easy to teach a wrong mental model; needs care)
- How does WiFi work? (invisible + abstract; low visual payoff)
