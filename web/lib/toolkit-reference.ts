/**
 * A condensed, hand-maintained API reference for engine/toolkit.py.
 *
 * The script writer needs to know every primitive it is allowed to call. It
 * cannot read the repo (the model runs before the sandbox exists), and pasting
 * the full 1,250-line module would cost ~15k tokens per draft for information
 * the writer does not need (implementation bodies).
 *
 * KEEP THIS IN SYNC when you add a primitive to engine/toolkit.py — a signature
 * that drifts here produces scene code that fails at render time, which the
 * user only discovers a minute into a build.
 */
export const TOOLKIT_REFERENCE = `
Canvas is 1920x1080 logical pixels. Origin top-left. \`d\` is the draw proxy.

LIFECYCLE
  img, d = tk.canvas(sky)            sky: "day" | "sunset" | "night" | "plain"
  return tk.vignette(img)            every scene function ends with this
  tk.save(img, path)                 handled by the render() helper, don't call

CONSTANTS
  tk.W, tk.H                         1920, 1080
  tk.SAFE                            (120, 80, 1800, 1000) — keep ALL text inside
  tk.PALETTE[k]  keys: sky_top sky_bottom grass grass_dark cloud cloud_shade sun
                 sun_deep rocket rocket_red rocket_dark window window_rim flame
                 flame_hot skin skin_dark hair shirt pants shoe ink white
                 molecule molecule_dark blue_ray red_ray star text text_dark
                 banner accent prism_glass
  tk.RAINBOW                         list of 7 (r,g,b) tuples

BACKGROUNDS
  tk.ground(d, y=880, color=None, dark=None, hills=True)
  tk.sea(d, y=760, color=None, deep=None, amp=16, wavelength=300, phase=0.0, foam=True)
  tk.cloud(d, x, y, scale=1.0, color=None, shade=True)
  tk.sun(d, x, y, r=120, rays=True, face=True, n_rays=12, ray_len=0.55, rotate=0.0)
  tk.stars(d, n=70, seed=3, area=(0,0,1920,760), color=None, twinkle=True)
  tk.mountain(d, x, y, w=520, h=420, color=None, shade=None, snow=True)   # feet at y

CHARACTERS
  tk.kid(d, x, y, scale=1.0, arms="down"|"up"|"one_up"|"point_up",
         mouth="smile"|"o"|"line", looking="up"|"front")                  # feet at y
  tk.rocket(d, x, y, scale=1.0, flame=True, tilt="up"|"right", face=False)
  tk.molecule(d, x, y, r=34, face=True, color=None, wobble=0.0)
  tk.molecule_field(d, n=60, seed=5, area=(120,140,1800,820), r_range=(20,40),
                    face=True, color=None)

PHYSICS / PROPS
  tk.zig_ray(d, p1, p2, color=None, amplitude=22, wavelength=110, width=9,
             phase=0.0, taper=False)          # wavy light ray; short wavelength = blue
  tk.arrow(d, p1, p2, color=None, width=12, head=34)
  tk.prism(d, x, y, size=260, color=None)
  tk.plane(d, x, y, scale=1.0, facing="right"|"left", pitch=0.0, windows=True)
  tk.paper_plane(d, x, y, scale=1.0, facing="right")
  tk.airfoil(d, x, y, scale=1.0, angle=8.0, outline_w=7)
  tk.wind_streaks(d, x, y, n=5, length=260, spread=150, width=10,
                  facing="right", curve=0.0, seed=2)
  tk.force_arrow(d, p1, p2, label, color=None, width=16, label_size=46)
  tk.planet(d, x, y, r=200, tilt=23.5, axis=True, land=True,
            night=None|"left"|"right", seed=3, face=False)
  tk.orbit_ring(d, cx, cy, rx, ry, color=None, width=7, dashes=56)
  tk.light_beam(d, start, end, n=5, spacing=74, color=None, width=11)
  tk.raindrop(d, x, y, size=44, color=None, shine=True)
  tk.rainfall(d, area, n=40, seed=7, size=(16,30), color=None, streaks=True)
  tk.puddle(d, x, y, w=300, h=70, color=None, shine=True)
  tk.cycle_arrow(d, cx, cy, rx, ry, start_deg, end_deg, color=None, width=14,
                 head=46, dashed=False)
  tk.wave(d, x, y, width=520, scale=1.0, color=None, deep=None, foam=True)
  tk.salt_crystal(d, x, y, size=90, color=None, sparkle=True, rotate=0.0)
  tk.river(d, points, width=70, color=None, taper=1.0, shine=True)   # points: [(x,y),...]

TEXT  (all of these register a bbox for the safe-zone check)
  tk.title_text(d, (x, y), text, size=96, fill=None, stroke=10, anchor="mm")
  tk.caption(d, text, size=58, y=950)                 # bottom banner, auto-shrinks
  tk.speech_pop(d, x, y, text, size=64, fill=None, text_fill=None)
  tk.badge(d, (x, y), text, size=54)
  tk.thought_bubble(d, x, y, w=620, h=300, tail_to=(x,y), text="", text_size=62)

LAYOUT
  zones = tk.end_screen_guides(d)     # returns dict; "end_cards" = bottom-right 40%
  tk.safe_zone_violations(zone)       # [] means compliant
`.trim();
