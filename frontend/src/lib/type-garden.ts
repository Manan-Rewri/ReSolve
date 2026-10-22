/**
 * Type Garden — monochrome ReSolve edition.
 *
 * A TypeScript port of "Type Garden" by Akshat Agarwal (type-garden.vercel.app),
 * recoloured to match the ReSolve brand: Space Grotesk Bold, black and white.
 * See AGENTS.md §6 — the brand has no accent colours, so the roses, stems,
 * leaves and butterflies are all neutral greys and whites.
 *
 * The garden is procedural: every letter seeds its own unique plant from a
 * deterministic PRNG, so the word always grows the same way.
 */

export const GARDEN_FONT = '"Space Grotesk", ui-sans-serif, system-ui, sans-serif'

export type GardenPalette = {
  name: string
  /** Page background. */
  bg: string
  /** Flower heads. Deliberately off-white so the wordmark stays dominant. */
  rose: string
  /** Stems and leaves. #6E6E6E is lifted straight from the ReSolve logo. */
  stem: string
  /** Petal outlines and stamen lines. */
  line: string
  /** The letters themselves — the brightest thing on screen. */
  text: string
  /** Leaf veins. Barely there on purpose. */
  vein: string
}

export const PALETTES: GardenPalette[] = [
  {
    name: 'Mono',
    bg: '#000000',
    rose: '#E8E8E8',
    stem: '#6E6E6E',
    line: '#B8B8B8',
    text: '#FFFFFF',
    vein: '#242424',
  },
]

const CONFIG = { boil: true, recoil: 20, density: 1 }

/** How long a letter takes to fade in, in ms. */
const FADE_MS = 700

type Point = [number, number]

type Segment = { u0: number; u1: number; layer: number }
type Thorn = { u: number; s: number }

type StemEl = {
  t: 'stem'
  id: number
  pts: Point[]
  segs: Segment[]
  d0: number
  dur: number
  w: number
  thorns: Thorn[]
}

type LeafEl = {
  t: 'leaf'
  id: number
  x: number
  y: number
  a: number
  L: number
  bend: number
  layer: number
  d0: number
}

type RoseEl = {
  t: 'rose'
  id: number
  x: number
  y: number
  R: number
  rot: number
  ph1: number
  ph2: number
  turns: number
  layer: number
  d0: number
}

type El = StemEl | LeafEl | RoseEl

type Letter = {
  ch: string
  id: number
  birth: number
  els: El[]
  endEls: El[] | null
  tend: StemEl[] | null
  cut: number | null
  tb: number
  dead: number | null
  ws: number
  wi: number
  prev: Letter | null
  tx: number
  ty: number
  tw: number
  line: number
  x: number
  y: number
  /** False until layout has pinned this letter to its final slot. */
  placed: boolean
  lean: [number, number]
}

type Gift = {
  x: number
  y: number
  t0: number
  rot: number
  e: { ph1: number; ph2: number; turns: number }
}

type Fly = {
  x: number
  y: number
  vx: number
  vy: number
  st: 'fly' | 'wander' | 'sit' | 'leave'
  pid: number | null
  hx: number
  hy: number
  t0: number
  ph: number
  sz: number
  seed: number
  ang: number
  ex?: number
  ey?: number
  open?: number
}

type Perch = { id: number; x: number; y: number; R: number }

type Backend = {
  fill: (pts: Point[], col: string) => void
  stroke: (pts: Point[], col: string, w: number) => void
  rect: (x: number, y: number, w: number, h: number, col: string) => void
  text: (ch: string, x: number, y: number, size: number, col: string) => void
}

export type GardenOptions = {
  canvas: HTMLCanvasElement
  host: HTMLElement
  /** Called once the intro has finished typing and the CTA may be revealed. */
  onReady?: () => void
  /** Called every frame with the Y offset (in CSS px) where the CTA should sit. */
  onCtaOffset?: (y: number) => void
  /** Word typed out on first load. May itself contain the mistake. */
  word?: string
  /**
   * The word it corrects itself into, once, at the end of the intro.
   *
   * The engine types `word` in full, then swaps the final character for the
   * final character of `correction`. Both strings must share a common prefix —
   * e.g. "ReSolvx" -> "ReSolve", "405" -> "404". Omit to skip the correction.
   */
  correction?: string
  /** Skip the intro and place the word immediately. */
  reducedMotion?: boolean
}

export class Garden {
  private F = GARDEN_FONT
  private SENT = String.fromCharCode(0x200b)
  private palette = 0

  private cv: HTMLCanvasElement
  private host: HTMLElement
  private onReady?: () => void
  private onCtaOffset?: (y: number) => void
  private word: string
  private correction?: string
  private reducedMotion: boolean

  private g: CanvasRenderingContext2D
  private letters: Letter[] = []
  private uid = 1
  private cache: Record<string, number> = {}
  private Sd = 0
  private St = 0
  private wrapped = false

  private t0 = performance.now()
  private lastKey = 0
  private rand = Math.random

  private mx: number | null = null
  private my: number | null = null
  private flies: Fly[] = []
  private perch: Perch[] = []
  private gifts: Gift[] = []

  private W = 0
  private H = 0
  private dpr = 1

  private cx = 0
  private cy = 0
  private ctx_ = 0
  private cty = 0

  private done = false
  private cc: GardenPalette
  private fa: Record<number, [number, number]> = {}
  private touch = false
  private ptype = 'mouse'
  private lastTap: { t: number; x: number; y: number } | null = null
  private lastPlant = 0

  private inp: HTMLInputElement
  private composing = false
  private iv = ''
  private _kd = false
  private raf = 0
  private disposers: (() => void)[] = []

  constructor(opts: GardenOptions) {
    this.cv = opts.canvas
    this.host = opts.host
    this.onReady = opts.onReady
    this.onCtaOffset = opts.onCtaOffset
    this.word = opts.word ?? 'ReSolve'
    this.correction = opts.correction
    this.reducedMotion = opts.reducedMotion ?? false

    const ctx = this.cv.getContext('2d')
    if (!ctx) throw new Error('Type Garden: 2D canvas context unavailable')
    this.g = ctx
    this.cc = PALETTES[0]

    this.inp = document.createElement('input')
    this.touch =
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(pointer: coarse)').matches

    this.bind()
    this.resize()

    // Re-measure once the real font arrives, otherwise the first layout is wrong.
    const load = document.fonts?.load?.(`700 100px ${GARDEN_FONT}`)
    load?.then(() => {
      this.cache = {}
      this.layout()
    }).catch(() => {})

    const loop = () => {
      this.raf = requestAnimationFrame(loop)
      this.frame()
    }
    loop()

    this.startIntro()
  }

  destroy() {
    cancelAnimationFrame(this.raf)
    for (const d of this.disposers) d()
    this.disposers = []
  }

  /* ------------------------------------------------------------------ */
  /* events                                                              */
  /* ------------------------------------------------------------------ */

  private listen<E extends Event>(
    target: Window | Document | HTMLElement,
    type: string,
    handler: (e: E) => void,
    opts?: boolean | AddEventListenerOptions,
  ) {
    const h = handler as EventListener
    target.addEventListener(type, h, opts)
    this.disposers.push(() => target.removeEventListener(type, h, opts))
  }

  private bind() {
    this.listen(window, 'resize', () => this.resize())

    this.listen(window, 'keydown', (e: KeyboardEvent) => this.key(e))

    this.listen(window, 'pointermove', (e: PointerEvent) => {
      this.mx = e.clientX
      this.my = e.clientY
    })
    this.listen(window, 'pointerdown', (e: PointerEvent) => {
      this.ptype = e.pointerType || 'mouse'
    }, true)

    const release = (e: PointerEvent) => {
      if (e.pointerType && e.pointerType !== 'mouse') this.mx = null
    }
    this.listen(window, 'pointerup', release)
    this.listen(window, 'pointercancel', release)
    this.listen(document, 'pointerleave', () => {
      this.mx = null
    })
    this.listen(document, 'mouseout', (e: MouseEvent) => {
      if (!e.relatedTarget) this.mx = null
    })

    this.inp.value = this.SENT
    this.iv = this.SENT
    this.inp.addEventListener('compositionstart', () => {
      this.composing = true
    })
    this.inp.addEventListener('compositionend', () => {
      this.composing = false
      setTimeout(() => {
        if (!this.composing) this.inputDiff(this.inp)
      }, 0)
    })
    this.inp.addEventListener('input', () => this.inputDiff(this.inp))

    this.listen(this.host, 'pointerdown', (ev: PointerEvent) => {
      const touch = ev.pointerType && ev.pointerType !== 'mouse'
      const onCanvas = ev.target === this.cv

      if (touch && ev.cancelable && onCanvas) ev.preventDefault()
      else if (!touch && onCanvas) this.refocus()

      if (!onCanvas) return

      this.spawnFly(ev.clientX, ev.clientY)

      const now = performance.now()
      const lp = this.lastTap
      this.lastTap = { t: now, x: ev.clientX, y: ev.clientY }
      // Double tap plants a rose. Gated so a triple tap doesn't stack.
      if (
        lp &&
        now - lp.t < 340 &&
        Math.hypot(ev.clientX - lp.x, ev.clientY - lp.y) < 40 &&
        now - this.lastPlant > 1800
      ) {
        this.lastPlant = now
        this.lastTap = null
        this.plant({
          x: ev.clientX / this.W,
          y: ev.clientY / this.H,
          s: Math.floor(Math.random() * 1e6),
        })
      }
    })

    this.listen(this.host, 'click', (ev: MouseEvent) => {
      if (this.ptype !== 'mouse' && ev.target === this.cv) this.refocus()
    })

    // Keep the page still when the mobile keyboard opens under the hidden input.
    if (window.visualViewport && this.touch) {
      const vv = window.visualViewport
      let maxH = 0
      let width = 0
      let kbWas = false

      const sync = () => {
        const w = Math.round(vv.width)
        if (width !== w) {
          width = w
          maxH = 0
        }
        maxH = Math.max(maxH, vv.height)
        const kb = maxH - vv.height > 120
        this.host.style.top = `${vv.offsetTop}px`
        this.host.style.bottom = 'auto'
        this.host.style.height = `${vv.height}px`
        if (!kb && kbWas && document.activeElement === this.inp) this.inp.blur()
        kbWas = kb
        this.resize()
      }

      vv.addEventListener('resize', sync)
      vv.addEventListener('scroll', sync)
      this.disposers.push(() => {
        vv.removeEventListener('resize', sync)
        vv.removeEventListener('scroll', sync)
      })
      sync()
    }
  }

  private refocus() {
    if (this.ptype === 'mouse') this.inp.focus({ preventScroll: true })
  }

  /* ------------------------------------------------------------------ */
  /* butterflies                                                         */
  /* ------------------------------------------------------------------ */

  private spawnFly(cx: number, cy: number) {
    if (this.flies.length >= 6) {
      const busy = this.flies.find((f) => f.st !== 'leave')
      if (busy) this.flyOff(busy)
    }

    const taken = new Set(this.flies.filter((f) => f.st !== 'leave').map((f) => f.pid))
    let best: Perch | null = null
    let bestDist = 1e9
    for (const p of this.perch) {
      if (taken.has(p.id)) continue
      const d = Math.hypot(p.x - cx, p.y - cy)
      if (d < bestDist) {
        bestDist = d
        best = p
      }
    }

    const left = cx < this.W / 2
    this.flies.push({
      x: left ? -40 : this.W + 40,
      y: cy + (Math.random() - 0.5) * this.H * 0.4,
      vx: 0,
      vy: 0,
      st: best ? 'fly' : 'wander',
      pid: best ? best.id : null,
      hx: cx,
      hy: cy,
      t0: performance.now(),
      ph: Math.random() * 6,
      sz: Math.max(9, this.Sd * 0.09),
      seed: Math.random() * 100,
      ang: 0,
    })
  }

  private flyOff(f: Fly) {
    f.st = 'leave'
    f.pid = null
    f.ex = f.x < this.W / 2 ? -80 : this.W + 80
    f.ey = f.y - this.H * 0.3
  }

  private drawFlies(B: Backend, now: number, C: GardenPalette) {
    const dt = Math.min(48, now - this.lastFlyTime)
    this.lastFlyTime = now

    const byId: Record<number, Perch> = {}
    for (const p of this.perch) byId[p.id] = p

    this.flies = this.flies.filter((f) => {
      const t = (now - f.t0) / 1000
      let tx = 0
      let ty = 0

      if (f.st === 'sit' || f.st === 'fly') {
        const p = byId[f.pid as number]
        if (!p) {
          this.flyOff(f)
        } else {
          tx = p.x + p.R * 0.05
          ty = p.y - p.R * 0.55
        }
      }
      if (f.st === 'wander') {
        tx = f.hx + Math.sin(t * 1.3 + f.seed) * 70
        ty = f.hy + Math.sin(t * 2.1 + f.seed) * 40
        if (t > 3.5) this.flyOff(f)
      }
      if (f.st === 'leave') {
        tx = f.ex as number
        ty = f.ey as number
      }

      if (f.st === 'sit') {
        f.x += (tx - f.x) * 0.35
        f.y += (ty - f.y) * 0.35
        f.ang *= 0.85
        f.ph += dt * 0.004
        const burst = Math.sin((now / 1000) * 0.9 + f.seed) > 0.75
        f.open = burst
          ? 0.2 + 0.8 * Math.abs(Math.cos((now / 1000) * 9 + f.seed))
          : 0.25 + 0.15 * Math.sin(f.ph)
      } else {
        const dx = tx - f.x
        const dy = ty - f.y
        const d = Math.hypot(dx, dy) || 1
        const sp = f.st === 'leave' ? 0.42 : Math.min(0.34, 0.06 + d * 0.0016)
        const flut = Math.sin(t * 7 + f.seed) * 0.12
        const wob = Math.cos(t * 4.3 + f.seed) * 0.1
        f.vx += ((dx / d) * sp + wob - f.vx) * ((0.06 * dt) / 16)
        f.vy += ((dy / d) * sp + flut - f.vy) * ((0.06 * dt) / 16)
        f.x += f.vx * dt
        f.y += f.vy * dt + Math.sin(t * 13 + f.seed) * 0.6
        f.ang += (Math.max(-0.5, Math.min(0.5, f.vx * 1.4)) - f.ang) * 0.1
        f.open = Math.abs(Math.cos(t * 17 + f.seed))
        if (f.st === 'fly' && d < 5) {
          f.st = 'sit'
          f.ph = 0
        }
        if (f.st === 'leave' && (f.x < -60 || f.x > this.W + 60 || f.y < -60)) return false
      }

      this.butterfly(B, f.x, f.y, f.sz, f.ang, f.open ?? 0, C)
      return true
    })
  }

  private lastFlyTime = 0

  private butterfly(B: Backend, x: number, y: number, s: number, ang: number, o: number, C: GardenPalette) {
    const ca = Math.cos(ang)
    const sa = Math.sin(ang)
    const T = (px: number, py: number): Point => [
      x + (px * ca - py * sa) * s,
      y + (px * sa + py * ca) * s,
    ]

    const wing = (cx: number, cy: number, rx: number, ry: number, a: number, side: number) => {
      const pts: Point[] = []
      const c = Math.cos(a)
      const sn = Math.sin(a)
      for (let k = 0; k < 22; k++) {
        const th = (k / 22) * Math.PI * 2
        const r = 1 + 0.08 * Math.sin(th * 3)
        const lx = Math.cos(th) * rx * r
        const ly = Math.sin(th) * ry * r
        pts.push(
          T(side * (cx + lx * c - ly * sn) * (0.12 + 0.88 * o), cy + lx * sn + ly * c),
        )
      }
      return pts
    }

    for (const sd of [-1, 1] as const) {
      B.fill(wing(0.46, 0.28, 0.36, 0.3, 0.5 * sd * sd, sd), C.text)
      B.fill(wing(0.55, -0.32, 0.55, 0.36, -0.55, sd), C.text)
      if (o > 0.35) B.fill(wing(0.66, -0.4, 0.13, 0.11, 0, sd), C.line)
    }

    const body: Point[] = []
    for (let k = 0; k < 18; k++) {
      const th = (k / 18) * Math.PI * 2
      body.push(T(Math.cos(th) * 0.08, Math.sin(th) * 0.48))
    }
    B.fill(body, C.text)

    const lw = Math.max(0.8, s * 0.05)
    B.stroke([T(0, -0.42), T(-0.14, -0.72), T(-0.24, -0.86)], C.text, lw)
    B.stroke([T(0, -0.42), T(0.14, -0.72), T(0.24, -0.86)], C.text, lw)
  }

  /* ------------------------------------------------------------------ */
  /* math helpers                                                        */
  /* ------------------------------------------------------------------ */

  private h(n: number) {
    const x = Math.sin(n) * 43758.5453
    return x - Math.floor(x)
  }

  /** Damped spring — the overshoot that makes each letter land. */
  private spr(t: number, k = 7, w = 16) {
    if (t <= 0) return 0
    return 1 - Math.exp(-t * k) * Math.cos(t * w)
  }

  /** Ease-out cubic. */
  private eo(t: number) {
    if (t <= 0) return 0
    if (t >= 1) return 1
    return 1 - Math.pow(1 - t, 3)
  }

  private rng(seed: number) {
    let s = seed | 0
    return () => {
      s = (s + 0x6d2b79f5) | 0
      let t = Math.imul(s ^ (s >>> 15), 1 | s)
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296
    }
  }

  private bez(a: Point, b: Point, c: Point, d: Point, n: number) {
    const P: Point[] = []
    for (let i = 0; i <= n; i++) {
      const t = i / n
      const u = 1 - t
      P.push([
        u * u * u * a[0] + 3 * u * u * t * b[0] + 3 * u * t * t * c[0] + t * t * t * d[0],
        u * u * u * a[1] + 3 * u * u * t * b[1] + 3 * u * t * t * c[1] + t * t * t * d[1],
      ])
    }
    return P
  }

  private at(P: Point[], u: number): [Point, number] {
    const n = P.length
    const i = Math.min(n - 2, Math.max(1, Math.round(u * (n - 1))))
    return [P[i], Math.atan2(P[i + 1][1] - P[i - 1][1], P[i + 1][0] - P[i - 1][0])]
  }

  private jit(id: number, f: number, amp: number): [number, number, number] {
    if (!amp) return [0, 0, 0]
    return [
      (this.h(id * 1.37 + f * 7.13) * 2 - 1) * amp,
      (this.h(id * 2.71 + f * 3.11) * 2 - 1) * amp,
      (this.h(id * 5.3 + f * 1.7) * 2 - 1) * 0.035,
    ]
  }

  private path(c: CanvasRenderingContext2D, p: Point[], closed: boolean) {
    const n = p.length
    if (n < 2) return
    const m = (a: Point, b: Point): Point => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]
    if (closed) {
      const s = m(p[n - 1], p[0])
      c.moveTo(s[0], s[1])
      for (let i = 0; i < n; i++) {
        const q = m(p[i], p[(i + 1) % n])
        c.quadraticCurveTo(p[i][0], p[i][1], q[0], q[1])
      }
      c.closePath()
    } else {
      c.moveTo(p[0][0], p[0][1])
      for (let i = 1; i < n - 1; i++) {
        const q = m(p[i], p[i + 1])
        c.quadraticCurveTo(p[i][0], p[i][1], q[0], q[1])
      }
      c.lineTo(p[n - 1][0], p[n - 1][1])
    }
  }

  private backend(g: CanvasRenderingContext2D): Backend {
    return {
      fill: (pts, col) => {
        g.beginPath()
        this.path(g, pts, true)
        g.fillStyle = col
        g.fill()
      },
      stroke: (pts, col, w) => {
        g.beginPath()
        this.path(g, pts, false)
        g.strokeStyle = col
        g.lineWidth = w
        g.lineCap = 'round'
        g.lineJoin = 'round'
        g.stroke()
      },
      rect: (x, y, w, h, col) => {
        g.fillStyle = col
        g.fillRect(x, y, w, h)
      },
      text: (ch, x, y, S, col) => {
        g.font = `700 ${S}px ${this.F}`
        g.textAlign = 'center'
        g.textBaseline = 'alphabetic'
        g.fillStyle = col
        g.fillText(ch, x, y)
      },
    }
  }

  private vine(base: Point, dir: number, len: number, amp: number, waves: number, ph: number, bend: number, n = 40) {
    const P: Point[] = [[base[0], base[1]]]
    const step = len / n
    let x = base[0]
    let y = base[1]
    for (let i = 1; i <= n; i++) {
      const u = i / n
      const a = dir + bend * u + amp * Math.sin(u * Math.PI * waves + ph) * Math.min(1, u * 3)
      x += Math.cos(a) * step
      y += Math.sin(a) * step
      P.push([x, y])
    }
    return P
  }

  private curl(P: Point[], sign: number, rad: number) {
    const n = P.length
    const e = P[n - 1]
    const a = Math.atan2(e[1] - P[n - 2][1], e[0] - P[n - 2][0])
    const c: Point = [e[0] - Math.sin(a) * sign * rad, e[1] + Math.cos(a) * sign * rad]
    const a0 = Math.atan2(e[1] - c[1], e[0] - c[0])
    for (let i = 1; i <= 14; i++) {
      const u = i / 14
      const t = a0 + sign * u * Math.PI * 1.6
      const rr = rad * (1 - 0.5 * u)
      P.push([c[0] + Math.cos(t) * rr, c[1] + Math.sin(t) * rr])
    }
    return P
  }

  /** Split a stem into over/under weaving segments so it reads as 3D. */
  private weave(r: () => number, startLayer: number) {
    const cuts: number[] = []
    const nc = 1 + Math.floor(r() * 3)
    for (let i = 0; i < nc; i++) cuts.push(0.15 + r() * 0.7)
    cuts.sort((a, b) => a - b)

    const segs: Segment[] = []
    let u0 = 0
    let layer = startLayer
    for (const c of cuts) {
      if (c <= u0) continue
      segs.push({ u0, u1: c, layer })
      if (r() < 0.3) {
        const g = 0.02 + r() * 0.03
        u0 = Math.min(0.98, c + g)
      } else {
        u0 = c
      }
      layer = 1 - layer
    }
    segs.push({ u0, u1: 1, layer })
    return segs
  }

  private layerAt(segs: Segment[], u: number) {
    for (const s of segs) if (u >= s.u0 && u <= s.u1) return s.layer
    return segs[segs.length - 1].layer
  }

  /* ------------------------------------------------------------------ */
  /* layout                                                              */
  /* ------------------------------------------------------------------ */

  private resize() {
    const r = this.host.getBoundingClientRect()
    const d = window.devicePixelRatio || 1
    if (!r.width) return
    this.W = r.width
    this.H = r.height
    this.dpr = d
    this.cv.width = Math.round(r.width * d)
    this.cv.height = Math.round(r.height * d)
    this.layout(true)
  }

  /** Per-character advance width, cached, normalised to font size 1. */
  private mw(ch: string) {
    const hit = this.cache[ch]
    if (hit != null) return hit
    this.g.font = `700 100px ${this.F}`
    let w = this.g.measureText(ch).width / 100
    if (ch === ' ') w *= 1.4
    this.cache[ch] = w
    return w
  }

  private layoutCore(A: Letter[], W: number, H: number, prevWrapped: boolean) {
    const maxW = W * 0.8
    const S0 = H * 0.28
    const LH = 2.1

    const ws = A.map((l) => this.mw(l.ch))
    const words: ({ idx: number[] } | { sp: true; idx: number[] })[] = []
    let cur: { idx: number[] } | null = null
    A.forEach((l, i) => {
      if (l.ch === ' ') {
        if (cur) {
          words.push(cur)
          cur = null
        }
        words.push({ sp: true, idx: [i] })
      } else {
        if (!cur) cur = { idx: [] }
        cur.idx.push(i)
      }
    })
    if (cur) words.push(cur)

    const lineW = (li: number[], S: number) => {
      let e = li.length
      while (e > 0 && A[li[e - 1]].ch === ' ') e--
      let w = 0
      for (let k = 0; k < e; k++) w += ws[li[k]]
      return w * S
    }

    const wrap = (S: number) => {
      const lines: number[][] = [[]]
      let lw = 0
      for (const w of words) {
        const ww = w.idx.reduce((s, i) => s + ws[i], 0) * S
        if (!('sp' in w) && lw > 0 && lw + ww > maxW) {
          lines.push([])
          lw = 0
        }
        lines[lines.length - 1].push(...w.idx)
        lw += ww
      }
      return lines
    }

    let lines = [A.map((_, i) => i)]
    const unit = lineW(lines[0], 1)
    let S = unit > 0 ? Math.min(S0, maxW / unit) : S0

    const multi = words.filter((w) => !('sp' in w)).length > 1
    let wrapped = multi && (S < H * 0.1 || (prevWrapped && S < H * 0.14))

    if (wrapped) {
      let lo = H * 0.03
      let hi = H * 0.15
      // Binary search the largest size where every wrapped line still fits.
      for (let k = 0; k < 22; k++) {
        const mid = (lo + hi) / 2
        const ls = wrap(mid)
        const ok = ls.every((li) => lineW(li, mid) <= maxW) && ls.length * LH * mid <= H * 0.82
        if (ok) lo = mid
        else hi = mid
      }
      S = lo
      lines = wrap(S)
      if (lines.length < 2) wrapped = false
    }

    const n = lines.length
    const lh = LH * S
    lines.forEach((li, k) => {
      let x = W / 2 - lineW(li, S) / 2
      const y = H / 2 + (k - (n - 1) / 2) * lh + 0.33 * S
      li.forEach((i) => {
        const l = A[i]
        const w = ws[i] * S
        l.tx = x + w / 2
        l.ty = y
        l.tw = w
        l.line = k
        x += w
      })
    })

    return { S, wrapped, n }
  }

  private layout(snap = false) {
    if (!this.W) return
    const A = this.letters.filter((l) => !l.dead)
    const res = this.layoutCore(A, this.W, this.H, this.wrapped)
    this.wrapped = res.wrapped
    for (const l of A) {
      if (!l.placed) {
        // Letters are born at their final slot, never at the origin. The
        // entrance is a fade (see render), not a flight across the canvas.
        l.x = l.tx
        l.y = l.ty
        l.placed = true
      }
    }

    const S = res.S
    const last = A[A.length - 1]
    this.St = S
    this.ctx_ = last ? last.tx + last.tw / 2 + 0.07 * S : this.W / 2
    this.cty = last ? last.ty - 0.33 * S : this.H / 2

    if (snap || !this.Sd) {
      this.Sd = S
      this.cx = this.ctx_
      this.cy = this.cty
      for (const l of A) {
        l.x = l.tx
        l.y = l.ty
      }
    }
  }

  /* ------------------------------------------------------------------ */
  /* intro                                                               */
  /* ------------------------------------------------------------------ */

  private startIntro() {
    const word = this.word

    if (this.reducedMotion) {
      const now = performance.now()
      for (const ch of this.finalWord()) this.add(ch, now)
      this.done = true
      this.onReady?.()
      return
    }

    const finish = () => {
      this.done = true
      this.onReady?.()
    }

    const fixed = this.correction?.[this.correction.length - 1]
    const current = word[word.length - 1]
    const corrects = !!fixed && fixed !== current

    const go = () => {
      let i = 0
      const step = () => {
        if (i < word.length) {
          const now = performance.now()
          this.lastKey = now
          this.add(word[i++], now)
          setTimeout(step, 170)
          return
        }

        // The word has landed, wrong character and all. Leave it there while
        // the caret blinks: the pause is what makes the next part read as a
        // correction rather than a glitch.
        setTimeout(() => {
          if (!corrects || !fixed) {
            finish()
            return
          }

          // Backspace. The wrong character is deleted and the letter before
          // it regrows the stem it had grown to reach it. The word itself
          // stays exactly where it was.
          const now = performance.now()
          this.lastKey = now
          this.wither(now, false)
          this.layoutAnchored()

          // Then the right character is typed, the same way every other
          // character in the word was.
          setTimeout(() => {
            const t = performance.now()
            this.lastKey = t
            this.add(fixed, t, false)
            this.layoutAnchored()
            setTimeout(finish, 1100)
          }, 320)
        }, corrects ? 1500 : 0)
      }
      setTimeout(step, 400)
    }

    const load = document.fonts?.load?.(`700 100px ${GARDEN_FONT}`)
    if (load?.then) load.then(go).catch(go)
    else go()
  }

  /**
   * Lay the word out again, keeping every line where it was.
   *
   * The layout centres each line, so deleting a character slides the whole
   * word sideways. A text editor does not do that — the text stays put and the
   * caret moves. This holds the line, so a deletion and its replacement happen
   * in place.
   */
  private layoutAnchored() {
    const anchor = new Map<number, number>()
    for (const l of this.letters) {
      if (l.dead || !l.placed || l.line == null) continue
      if (!anchor.has(l.line)) anchor.set(l.line, l.tx)
    }
    const wasPlaced = new Set(
      this.letters.filter((l) => !l.dead && l.placed).map((l) => l.id),
    )

    this.layout()

    // The layout re-centred each line. Move it back to where it was.
    const shift = new Map<number, number>()
    for (const l of this.letters) {
      if (l.dead || !l.placed || l.line == null) continue
      const at = anchor.get(l.line)
      if (at == null) continue
      if (!shift.has(l.line)) shift.set(l.line, at - l.tx)
    }
    for (const l of this.letters) {
      if (l.dead || !l.placed || l.line == null) continue
      const d = shift.get(l.line)
      if (d == null) continue
      l.tx += d
      // A letter that had only just been placed snapped to the unshifted slot,
      // so it has to travel with the rest of the line.
      if (!wasPlaced.has(l.id)) l.x += d
    }

    // The caret sits after the last letter, so it has to move with it.
    const last = this.letters.filter((l) => !l.dead).pop()
    if (last) {
      this.ctx_ = last.tx + last.tw / 2 + 0.07 * this.St
      this.cty = last.ty - 0.33 * this.St
    }
  }

  /** What the word should end up as — the correction if there is one. */
  private finalWord(): string {
    const fixed = this.correction?.[this.correction.length - 1]
    return fixed && fixed !== this.word[this.word.length - 1]
      ? this.word.slice(0, -1) + fixed
      : this.word
  }

  private placeCta() {
    const S = this.St || this.Sd || 0
    const y = (this.cty || this.H / 2) + S * 0.33 + S * 0.42
    this.onCtaOffset?.(Math.min(y, this.H - 90))
  }

  private plant(g: { x: number; y: number; s: number }) {
    const r = this.rng((g.s | 0) || 1)
    this.gifts.push({
      x: Math.min(1, Math.max(0, g.x)),
      y: Math.min(1, Math.max(0, g.y)),
      t0: performance.now(),
      rot: (r() - 0.5) * 0.8,
      e: { ph1: r() * 6.283, ph2: r() * 6.283, turns: 1.4 + r() * 0.5 },
    })
    if (this.gifts.length > 14) this.gifts.shift()
  }

  /* ------------------------------------------------------------------ */
  /* typing input                                                        */
  /* ------------------------------------------------------------------ */

  private wither(now: number, relayout = true) {
    const A = this.letters.filter((l) => !l.dead)
    const last = A[A.length - 1]
    if (!last) return
    last.dead = now
    const prev = A[A.length - 2]
    if (prev && prev.ch !== ' ') {
      prev.cut = null
      prev.endEls = null
      prev.tb = now
    }
    if (relayout) this.layout()
  }

  private inputDiff(el: HTMLInputElement) {
    const S = this.SENT
    // `_kd` means this input event was synthesised by our own keydown handler.
    if (this._kd) {
      this.iv = this.composing ? el.value : S
      if (!this.composing) el.value = S
      return
    }

    const old = this.iv == null ? S : this.iv
    const cur = el.value

    let p = 0
    while (p < old.length && p < cur.length && old[p] === cur[p]) p++
    let dels = old.length - p
    if (p === 0 && old[0] === S && old.length > 1) dels -= 1

    const now = performance.now()
    this.lastKey = now
    for (let i = 0; i < dels; i++) this.wither(now)

    for (const ch of cur.slice(p)) {
      if (ch === S) continue
      if (ch.charCodeAt(0) === 10) {
        this.letters = []
        this.layout()
      } else {
        this.add(ch, now)
      }
    }

    if (this.composing) this.iv = cur
    else {
      el.value = S
      this.iv = S
    }
  }

  private key(e: KeyboardEvent) {
    if (e.metaKey || e.ctrlKey || e.altKey) return

    // Never hijack typing into a real field.
    const target = e.target as HTMLElement | null
    const tag = target?.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || target?.isContentEditable) return
    if (tag === 'BUTTON' && (e.key === 'Enter' || e.key === ' ')) return

    const now = performance.now()
    if (e.key === 'Backspace') {
      e.preventDefault()
      this.mark()
      this.wither(now)
      return
    }
    if (e.key === 'Enter') {
      e.preventDefault()
      this.mark()
      this.letters = []
      this.layout()
      return
    }
    if (e.key.length !== 1) return
    e.preventDefault()
    this.mark()
    this.add(e.key, now)
  }

  private mark() {
    this.lastKey = performance.now()
    this._kd = true
    setTimeout(() => {
      this._kd = false
    }, 0)
  }

  private add(ch: string, now: number, relayout = true) {
    const A = this.letters.filter((l) => !l.dead)
    const last = A[A.length - 1]

    if (ch === ' ') {
      if (last && last.ch !== ' ') {
        last.cut = now
        this.genEnd(last, now - last.birth)
      }
      this.letters.push({
        ch: ' ',
        id: this.uid++,
        birth: now,
        els: [],
        endEls: null,
        tend: null,
        cut: null,
        tb: now,
        dead: null,
        ws: 0,
        wi: 0,
        prev: null,
        tx: 0,
        ty: 0,
        tw: 0,
        line: 0,
        x: 0,
        y: 0,
        placed: false,
        lean: [0, 0],
      })
      this.layout()
      return
    }

    const same = !!last && last.ch !== ' '
    const l: Letter = {
      ch,
      id: this.uid++,
      birth: now,
      els: [],
      endEls: null,
      tend: null,
      cut: null,
      tb: now,
      dead: null,
      ws: same ? last.ws : Math.floor(this.rand() * 1e9),
      wi: same ? last.wi + 1 : 0,
      prev: same ? last : null,
      tx: 0,
      ty: 0,
      tw: 0,
      line: 0,
      x: 0,
      y: 0,
      placed: false,
      lean: [0, 0],
    }
    this.gen(l)
    this.letters.push(l)
    if (relayout) this.layout()
  }

  /* ------------------------------------------------------------------ */
  /* procedural growth                                                   */
  /* ------------------------------------------------------------------ */

  private wordParams(ws: number) {
    const r = this.rng(ws * 7 + 13)
    const dens = CONFIG.density
    return {
      roseP: 0.3 + r() * 0.3,
      leafy: (0.6 + r() * 0.8) * dens,
      dens,
      lean: (r() - 0.5) * 0.6,
      big: 0.85 + r() * 0.45,
      curvy: 0.8 + r() * 0.6,
      bridgeP: Math.min(0.95, (0.45 + r() * 0.35) * dens),
      w: 0.5,
    }
  }

  private grow(
    r: () => number,
    E: El[],
    nid: () => number,
    p: ReturnType<Garden['wordParams']>,
    o: {
      base?: Point
      dir?: number
      len?: number
      d0?: number
      depth?: number
      layer0?: number
      pts?: Point[]
      tip?: string | null
    },
  ) {
    const tip =
      o.tip || (r() < p.roseP ? 'rose' : r() < 0.45 ? 'fan' : r() < 0.6 ? 'leaf' : 'curl')

    let P =
      o.pts ||
      this.vine(
        o.base as Point,
        o.dir as number,
        o.len as number,
        (0.35 + r() * 0.45) * p.curvy,
        1 + r() * 1.6,
        r() * 6.28,
        (r() - 0.5) * 1.2,
        40,
      )
    if (tip === 'curl') P = this.curl(P, r() < 0.5 ? -1 : 1, 0.05 + r() * 0.05)

    const segs = this.weave(r, o.layer0 != null ? o.layer0 : r() < 0.5 ? 0 : 1)
    const dur = Math.max(320, (o.len || 0.8) * 620)

    const thorns: Thorn[] = []
    const nt = Math.floor(r() * 2.5)
    for (let i = 0; i < nt; i++) thorns.push({ u: 0.15 + r() * 0.65, s: r() < 0.5 ? -1 : 1 })

    E.push({
      t: 'stem',
      id: nid(),
      pts: P,
      segs,
      d0: o.d0 as number,
      dur,
      w: o.depth ? 0.82 : 1,
      thorns,
    })

    const nl = Math.floor(r() * 2.8 * p.leafy)
    let sd = r() < 0.5 ? -1 : 1
    for (let i = 0; i < nl; i++) {
      const u = 0.25 + r() * 0.6
      const [q, a] = this.at(P, u)
      sd = -sd
      E.push({
        t: 'leaf',
        id: nid(),
        x: q[0],
        y: q[1],
        a: a + sd * (0.55 + r() * 0.5),
        L: (0.14 + r() * 0.2) * (o.depth ? 0.8 : 1),
        bend: (r() - 0.5) * 1.2,
        layer: this.layerAt(segs, u),
        d0: (o.d0 as number) + dur * u,
      })
    }

    const [tp, ta] = this.at(P, 1)
    const td = (o.d0 as number) + dur * 0.8
    const tl = this.layerAt(segs, 1)

    if (tip === 'rose') {
      const R = (0.13 + r() * 0.15) * p.big * (o.depth ? 0.75 : 1)
      const over = tp[1] > -0.78 && tp[1] < 0.05 && Math.abs(tp[0]) < p.w * 0.5
      const layer = over ? (r() < 0.22 ? 1 : 0) : r() < 0.6 ? 1 : tl
      E.push({
        t: 'rose',
        id: nid(),
        x: tp[0],
        y: tp[1],
        R,
        rot: (r() - 0.5) * 1.0,
        ph1: r() * 6.28,
        ph2: r() * 6.28,
        turns: 1.8 + r(),
        layer,
        d0: td,
      })
      if (r() < 0.2) {
        const oo = ta + (r() < 0.5 ? 1 : -1) * 1.3
        E.push({
          t: 'rose',
          id: nid(),
          x: tp[0] + Math.cos(oo) * R * 1.4,
          y: tp[1] + Math.sin(oo) * R * 1.4,
          R: R * (0.6 + r() * 0.3),
          rot: (r() - 0.5) * 1.2,
          ph1: r() * 6.28,
          ph2: r() * 6.28,
          turns: 1.8 + r(),
          layer,
          d0: td + 120,
        })
      }
    } else if (tip === 'fan') {
      const spread = 0.6 + r() * 0.3
      for (let j = 0; j < 2; j++) {
        E.push({
          t: 'leaf',
          id: nid(),
          x: tp[0],
          y: tp[1],
          a: ta + (j - 0.5) * spread,
          L: 0.2 + r() * 0.2,
          bend: (j - 0.5) * 0.8,
          layer: tl,
          d0: td + j * 60,
        })
      }
    } else if (tip === 'leaf') {
      E.push({
        t: 'leaf',
        id: nid(),
        x: tp[0],
        y: tp[1],
        a: ta + (r() - 0.5) * 0.3,
        L: 0.16 + r() * 0.16,
        bend: r() - 0.5,
        layer: tl,
        d0: td,
      })
    }

    if (!o.depth && r() < 0.3) {
      const u = 0.35 + r() * 0.35
      const [q, a] = this.at(P, u)
      this.grow(r, E, nid, p, {
        base: q,
        dir: a + (r() < 0.5 ? -1 : 1) * (0.7 + r() * 0.4),
        len: (o.len || 0.8) * (0.35 + r() * 0.2),
        d0: (o.d0 as number) + dur * u,
        depth: 1,
        layer0: this.layerAt(segs, u),
      })
    }

    return P
  }

  private gen(l: Letter) {
    const r = this.rng((l.ws ^ Math.imul(l.wi + 1, 2654435761)) + Math.floor(this.rand() * 1e6))
    const p = this.wordParams(l.ws)
    const E: El[] = []
    let k0 = 0
    const nid = () => l.id * 100 + k0++

    const w = this.mw(l.ch)
    const inX = () => (r() - 0.5) * w * 0.7
    p.w = w

    const nUp = 1 + (r() < 0.45 * p.dens ? 1 : 0)
    for (let i = 0; i < nUp; i++) {
      this.grow(r, E, nid, p, {
        base: [inX(), -r() * 0.3],
        dir: -Math.PI / 2 + p.lean * 0.5 + (r() - 0.5) * 0.7,
        len: 0.6 + r() * 0.5,
        d0: 40 + i * 130,
        tip: l.wi === 0 && i === 0 ? 'rose' : null,
      })
    }

    if (r() < 0.4 * p.dens) {
      this.grow(r, E, nid, p, {
        base: [inX(), -0.1 - r() * 0.35],
        dir: Math.PI / 2 + (r() - 0.5) * 0.8,
        len: 0.35 + r() * 0.35,
        d0: 160,
      })
    }

    // A tendril bridging back to the previous letter.
    if (l.prev && r() < p.bridgeP) {
      const px = -(this.mw(l.prev.ch) + w) / 2
      const a: Point = [inX(), -0.05 - r() * 0.55]
      const b: Point = [px + (r() - 0.5) * 0.25, -0.05 - r() * 0.55]
      const bulge = (r() < 0.55 ? -1 : 1) * (0.4 + r() * 0.4)
      const dx = b[0] - a[0]
      let P = this.bez(
        a,
        [a[0] + dx * 0.15, a[1] + bulge],
        [b[0] - dx * 0.15, b[1] + bulge * 0.9],
        b,
        40,
      )
      if (r() < 0.45) P = P.slice(0, Math.floor(P.length * (0.7 + r() * 0.2)))
      this.grow(r, E, nid, p, {
        pts: P,
        len: Math.abs(dx) + Math.abs(bulge),
        d0: 90,
        tip: r() < 0.5 ? 'curl' : r() < 0.5 ? 'leaf' : 'rose',
      })
    }

    if (l.wi === 0) {
      this.grow(r, E, nid, p, {
        base: [-w * 0.3, -0.15 - r() * 0.4],
        dir: Math.PI + (r() - 0.5) * 1.2,
        len: 0.45 + r() * 0.3,
        d0: 120,
        tip: 'curl',
      })
    }

    l.els = E
    l.endEls = null

    // The tendril that extends when the letter ends a word.
    const T: El[] = []
    const tr = this.rng(l.id * 977 + Math.floor(this.rand() * 1e6))
    this.grow(tr, T, () => l.id * 100 + 90 + T.length, p, {
      base: [w * 0.25, -0.1 - tr() * 0.45],
      dir: (tr() - 0.5) * 1.4,
      len: 0.45 + tr() * 0.25,
      d0: 0,
      tip: 'curl',
      depth: 1,
    })
    l.tend = T.filter((e): e is StemEl => e.t === 'stem').slice(0, 1)
  }

  private genEnd(l: Letter, rel: number) {
    const r = this.rng(l.ws + l.wi * 31 + Math.floor(this.rand() * 1e6))
    const p = this.wordParams(l.ws)
    const E: El[] = []
    let k0 = 50
    const nid = () => l.id * 100 + k0++

    const w = this.mw(l.ch)
    const n = 1 + Math.floor(r() * 2.5)
    p.w = w

    for (let i = 0; i < n; i++) {
      const dir = -Math.PI / 2 + 0.6 + (i - (n - 1) / 2) * 0.9 + (r() - 0.5) * 0.4
      this.grow(r, E, nid, p, {
        base: [(r() - 0.2) * w * 0.6, -r() * 0.5],
        dir,
        len: 0.4 + r() * 0.45,
        d0: rel + 40 + i * 90,
        depth: 1,
        tip: i === 0 || r() < 0.5 ? 'rose' : 'fan',
      })
    }

    l.endEls = E
  }

  /* ------------------------------------------------------------------ */
  /* drawing primitives                                                  */
  /* ------------------------------------------------------------------ */

  private strokeRange(B: Backend, P: Point[], a: number, b: number, col: string, w: number) {
    const n = P.length - 1
    const ia = a * n
    const ib = b * n
    const lerp = (t: number): Point => {
      const i = Math.min(n - 1, Math.floor(t))
      const f = t - i
      return [P[i][0] + (P[i + 1][0] - P[i][0]) * f, P[i][1] + (P[i + 1][1] - P[i][1]) * f]
    }
    const pts = [lerp(ia)]
    for (let i = Math.floor(ia) + 1; i < ib; i++) pts.push(P[i])
    pts.push(lerp(ib))
    if (pts.length >= 2) B.stroke(pts, col, w)
  }

  private thorn(B: Backend, P: Point[], u: number, s: number, S: number) {
    const [p, a] = this.at(P, u)
    const d = a + s * 2.3
    const L = S * 0.045
    B.stroke([p, [p[0] + Math.cos(d) * L, p[1] + Math.sin(d) * L]], this.cc.stem, S * 0.022)
  }

  private leaf(B: Backend, bx: number, by: number, a: number, L: number, bend: number) {
    if (L < 0.5) return
    const ca = Math.cos(a)
    const sa = Math.sin(a)
    const px = -sa
    const py = ca
    const ax = (u: number): Point => {
      const b = Math.sin(Math.PI * u) * bend * 0.15 * L
      return [bx + ca * u * L + px * b, by + sa * u * L + py * b]
    }
    const hw = (u: number) => L * 0.18 * Math.sin(Math.PI * Math.pow(u, 0.8))

    const N = 12
    const s1: Point[] = []
    const s2: Point[] = []
    for (let i = 0; i <= N; i++) {
      const u = i / N
      const c = ax(u)
      const w = hw(u)
      s1.push([c[0] + px * w, c[1] + py * w])
      s2.push([c[0] - px * w, c[1] - py * w])
    }

    const tip = ax(1)
    const base = ax(0)
    B.fill([base, ...s1.slice(1, N), tip, tip, ...s2.slice(1, N).reverse(), base], this.cc.stem)

    if (L > 6) {
      const v: Point[] = []
      for (let i = 0; i <= 8; i++) v.push(ax(0.08 + (0.72 * i) / 8))
      B.stroke(v, this.cc.vein, Math.max(0.8, L * 0.03))
    }
  }

  private rose(
    B: Backend,
    cx: number,
    cy: number,
    R: number,
    rot: number,
    e: RoseEl,
    a: number,
    tl: [number, number] | null,
  ) {
    const cr = Math.cos(rot)
    const sr = Math.sin(rot)
    const tm = tl ? Math.hypot(tl[0], tl[1]) : 0
    const ux = tm ? tl![0] / tm : 0
    const uy = tm ? tl![1] / tm : 0
    const sq = -0.28 * tm

    const T = (x: number, y: number, z = 0): Point => {
      let dx = x * cr - y * sr
      let dy = x * sr + y * cr
      if (tm) {
        const k = (dx * ux + dy * uy) * sq
        dx += k * ux + tl![0] * R * z
        dy += k * uy + tl![1] * R * z
      }
      return [cx + dx, cy + dy]
    }

    // x, y, rx, ry, angle, z, outlined
    const P: [number, number, number, number, number, number, number][] = [
      [0, -0.36, 0.56, 0.54, 0, 0, 0],
      [-0.5, -0.06, 0.6, 0.6, -0.35, 0, 0],
      [0.52, -0.06, 0.6, 0.6, 0.35, 0, 0],
      [-0.42, 0.3, 0.62, 0.48, 0.2, 0.12, 1],
      [0.47, 0.3, 0.62, 0.48, -0.2, 0.12, 1],
      [0.05, 0.42, 0.56, 0.38, 0, 0.14, 0],
    ]

    const ax0 = 0
    const ay0 = 0.5
    const lw = Math.max(0.8, R * 0.045)
    const st = 85

    P.forEach((q, i) => {
      const s = this.spr((a - i * st) / 1000, 8, 14)
      if (s <= 0.001) return
      const open = (1 - Math.min(1, s)) * (q[0] < 0 ? 0.5 : -0.5)
      const ang = q[4] + open
      const ca = Math.cos(ang)
      const sa = Math.sin(ang)

      const pt = (th: number): Point => {
        const rr = 1 + 0.08 * Math.sin(3 * th + e.ph1 + i) + 0.04 * Math.sin(5 * th + e.ph2)
        const lx = Math.cos(th) * q[2] * rr
        const ly = Math.sin(th) * q[3] * rr
        const px = q[0] + lx * ca - ly * sa
        const py = q[1] + lx * sa + ly * ca
        return T((ax0 + (px - ax0) * s) * R, (ay0 + (py - ay0) * s) * R, q[5])
      }

      const pts: Point[] = []
      for (let k = 0; k < 26; k++) pts.push(pt((k / 26) * Math.PI * 2))
      B.fill(pts, this.cc.rose)

      if (q[6] && R >= 12 && s > 0.4) {
        const arc: Point[] = []
        for (let k = 0; k <= 14; k++) arc.push(pt(Math.PI * (1.18 + (0.64 * k) / 14)))
        this.strokeRange(B, arc, 0, Math.min(1, (s - 0.4) / 0.5), this.cc.line, lw * 0.8)
      }
    })

    // Stamen spiral + sepal.
    const fr = this.eo((a - P.length * st - 80) / 520)
    if (fr > 0 && R > 3) {
      const sp: Point[] = []
      const scl: Point[] = []
      const turns = R < 20 ? Math.min(e.turns, 1.3) : R < 32 ? e.turns * 0.8 : e.turns
      for (let i = 0; i <= 70; i++) {
        const u = i / 70
        const th = e.ph1 + u * turns * Math.PI * 2
        const rr = R * (0.08 + 0.57 * u)
        sp.push(T(Math.cos(th) * rr * 1.05, Math.sin(th) * rr * 0.72 - 0.12 * R, 0.34 - 0.24 * u))
      }
      this.strokeRange(B, sp, 0, fr, this.cc.line, lw)

      if (R >= 14) {
        for (let i = 0; i <= 36; i++) {
          const u = i / 36
          scl.push(T(
            (-0.72 + 1.5 * u) * R,
            0.36 * R + 0.16 * R * Math.abs(Math.sin(u * Math.PI * 3)),
            0.18,
          ))
        }
        this.strokeRange(B, scl, 0, fr, this.cc.line, lw)
      }
    }
  }

  /** Roses turn to look at the cursor. */
  private faceTurn(e: RoseEl, x: number, y: number): [number, number] {
    let wx = 0
    let wy = 0

    if (this.mx != null && this.my != null) {
      const dx = this.mx - x
      const dy = this.my - y
      const d = Math.hypot(dx, dy)
      const reach = 300
      if (d < reach && d > 0.001) {
        const w = 1 - d / reach
        const s = w * w * (3 - 2 * w) * Math.min(1, d / 40)
        wx = (dx / d) * s
        wy = (dy / d) * s
      }
    }

    const c = this.fa[e.id] || [0, 0]
    c[0] += (wx - c[0]) * 0.09
    c[1] += (wy - c[1]) * 0.09
    this.fa[e.id] = c
    return c
  }

  /* ------------------------------------------------------------------ */
  /* render loop                                                         */
  /* ------------------------------------------------------------------ */

  private frame() {
    const now = performance.now()
    const dt = Math.min(64, now - (this.lastFrame || now))
    this.lastFrame = now
    if (!this.W) return

    const k = 1 - Math.exp(-dt / 80)
    this.Sd += (this.St - this.Sd) * k
    this.cx += (this.ctx_ - this.cx) * k
    this.cy += (this.cty - this.cy) * k

    for (const l of this.letters) {
      if (!l.dead && l.placed && l.tx != null) {
        l.x += (l.tx - l.x) * k
        l.y += (l.ty - l.y) * k
      }
    }

    this.letters = this.letters.filter((l) => !(l.dead && now - (l.dead as number) > 300))

    this.paint(now, !this.done)
    this.placeCta()
  }

  private lastFrame = 0

  private paint(now: number, caret: boolean) {
    const g = this.g
    const d = this.dpr
    g.setTransform(d, 0, 0, d, 0, 0)
    g.fillStyle = this.cc.bg
    g.fillRect(0, 0, this.W, this.H)

    const B = this.backend(g)
    this.render(B, now)
    this.drawFlies(B, now, this.cc)

    // Hand-planted roses.
    if (caret && this.gifts.length) {
      const LIFE = 60000
      this.gifts = this.gifts.filter((gf) => now - gf.t0 < LIFE)
      for (const gf of this.gifts) {
        const age = now - gf.t0
        const w = 1 - this.eo((age - (LIFE - 2200)) / 2200)
        g.globalAlpha = Math.max(0, w)
        this.rose(
          B,
          gf.x * this.W,
          gf.y * this.H + (1 - w) * this.Sd * 0.3,
          this.Sd * 0.24 * (0.65 + 0.35 * w),
          gf.rot + (1 - w) * 0.6,
          {
            t: 'rose',
            id: 0,
            x: 0,
            y: 0,
            R: 1,
            rot: 0,
            ph1: gf.e.ph1,
            ph2: gf.e.ph2,
            turns: gf.e.turns,
            layer: 0,
            d0: 0,
          },
          age,
          null,
        )
      }
      g.globalAlpha = 1
    }

    // Blinking caret.
    if (caret) {
      const S = this.Sd
      const on = now - this.lastKey < 500 || Math.floor(now / 530) % 2 === 0
      const hf = this.eo((now - this.t0) / 600)
      if (on && hf > 0) {
        const h = 0.8 * S * hf
        const w = Math.max(2, S * 0.03)
        B.rect(this.cx - w / 2, this.cy - h / 2, w, h, this.cc.text)
      }
    }
  }

  private render(B: Backend, now: number) {
    const S = this.Sd
    const L = this.letters
    const act = L.filter((l) => !l.dead)

    this.cc = PALETTES[this.palette] ?? PALETTES[0]
    this.now = now
    this.perch = []

    // Pre-compute cursor lean per letter so elements can be displaced.
    for (const l of L) {
      let tx = 0
      let ty = 0
      const A = !l.dead && l.ch !== ' ' && this.mx != null && this.my != null
        ? ([this.mx, this.my] as Point)
        : null
      if (A) {
        const dx = A[0] - l.x
        const dy = A[1] - (l.y - S * 0.6)
        const d = Math.hypot(dx, dy)
        const reach = Math.max(260, S * 3.2)
        if (d < reach && d > 1) {
          const w = 1 - d / reach
          const s = w * w * (3 - 2 * w)
          tx = (dx / d) * s
          ty = (dy / d) * s
        }
      }
      l.lean[0] += (tx - l.lean[0]) * 0.07
      l.lean[1] += (ty - l.lean[1]) * 0.07
    }

    const f = CONFIG.boil ? Math.floor(now / 120) : 0
    const amp = CONFIG.boil ? Math.max(0.8, S * 0.01) : 0
    const kd = (l: Letter) => (l.dead ? 1 - this.eo((now - (l.dead as number)) / 260) : 1)
    // Entrance is a fade, not a move. Each letter and the plant it seeds share
    // one alpha ramp so they emerge together.
    const fade = (l: Letter) => this.eo(Math.min(1, (now - l.birth) / FADE_MS))

    const draw = (layer: number) => {
      for (const l of L) {
        if (l.ch === ' ' || !l.els.length) continue
        const age = now - l.birth
        const kk = kd(l)

        this.g.globalAlpha = fade(l)

        const each = (e: El) => {
          if (e.t === 'stem') this.drawStem(B, e, l, age, kk, f, amp, layer)
          else if (e.layer === layer) this.drawEl(B, e, l, age, kk, f, amp)
        }

        for (const e of l.els) each(e)
        if (l.endEls) for (const e of l.endEls) each(e)

        const i = act.indexOf(l)
        const nx = i >= 0 ? act[i + 1] : null
        if (l.tend && (l.dead || !nx || nx.ch === ' ')) {
          let fr = this.eo((now - l.tb - 150) / 450)
          if (l.cut != null) {
            fr *= 1 - this.eo((now - l.cut) / 150) * Math.min(0.85, CONFIG.recoil / (0.6 * S))
          }
          for (const e of l.tend) this.drawStem(B, e, l, age, kk, f, amp, layer, fr * kk)
        }

        this.g.globalAlpha = 1
      }
    }

    draw(0)

    for (const l of L) {
      if (l.ch === ' ') continue
      // A dying letter keeps its glyph and fades with its vine. Skipping dead
      // letters here made the wrong character pop out of existence while the
      // stem around it lingered, which read as a glitch rather than a
      // correction.
      this.g.globalAlpha = fade(l) * kd(l)
      B.text(l.ch, l.x, l.y, S, this.cc.text)
    }
    this.g.globalAlpha = 1

    draw(1)
  }

  private now = 0

  /** Displace a plant element by the letter's landing bounce + cursor lean. */
  private wpt(l: Letter, x: number, y: number): Point {
    const S = this.Sd
    if (l.birth != null && this.now != null) {
      const t = (this.now - l.birth) / 1000
      if (t > 0 && t < 2.5) {
        const hh = Math.max(0, (l.y - y) / S)
        const dmp = Math.exp(-t * 3.2)
        const dir = l.id % 2 ? 1 : -1
        x += S * 0.07 * hh * dmp * Math.sin(t * 11) * dir
        y += S * 0.035 * hh * dmp * Math.sin(t * 11 + 1.2)
      }
    }
    const hh2 = Math.min(2.5, Math.max(0, (l.y - y) / S))
    const ff = hh2 * hh2 * 0.5 + hh2 * 0.5
    x += l.lean[0] * S * 0.1 * ff
    y += l.lean[1] * S * 0.05 * ff
    return [x, y]
  }

  private drawStem(
    B: Backend,
    e: StemEl,
    l: Letter,
    age: number,
    kk: number,
    f: number,
    amp: number,
    layer: number,
    frO?: number,
  ) {
    const S = this.Sd
    const fr = frO != null ? frO : this.eo((age - e.d0) / e.dur) * kk
    if (fr <= 0) return

    const j = this.jit(e.id, f, amp)
    const P = e.pts.map((p) => this.wpt(l, l.x + p[0] * S + j[0], l.y + p[1] * S + j[1]))

    for (const sg of e.segs) {
      if (sg.layer !== layer) continue
      const b = Math.min(sg.u1, fr)
      if (b <= sg.u0) continue
      this.strokeRange(B, P, sg.u0, b, this.cc.stem, S * 0.022 * (e.w || 1))
    }

    for (const th of e.thorns) {
      if (fr > th.u && this.layerAt(e.segs, th.u) === layer) this.thorn(B, P, th.u, th.s, S)
    }
  }

  private drawEl(B: Backend, e: El, l: Letter, age: number, kk: number, f: number, amp: number) {
    const S = this.Sd
    const j = this.jit(e.id, f, amp)
    const wx = (x: number, y: number) => this.wpt(l, l.x + x * S + j[0], l.y + y * S + j[1])

    if (e.t === 'leaf') {
      const sc = this.spr((age - e.d0) / 1000, 7, 15) * kk
      if (sc <= 0) return
      const p = wx(e.x, e.y)
      this.leaf(B, p[0], p[1], e.a + j[2], e.L * S * sc, e.bend)
    } else if (e.t === 'rose') {
      const a = age - e.d0
      if (a < 0 || kk <= 0.001) return
      const p = wx(e.x, e.y)
      const tl = this.faceTurn(e, p[0], p[1])
      if (!l.dead && a > 700) {
        this.perch.push({ id: e.id, x: p[0], y: p[1], R: e.R * S * kk })
      }
      this.rose(B, p[0], p[1], e.R * S * kk, e.rot + j[2] + tl[0] * 0.22, e, a, tl)
    }
  }
}
