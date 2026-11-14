import { useEffect, useRef } from 'react'
import { geoGraticule10, geoOrthographic, geoPath, type GeoPermissibleObjects } from 'd3-geo'

interface GlobeLoaderProps {
  /** Edge of the square canvas, in CSS pixels. */
  size?: number
  /** Accessible name; the loader itself never renders visible text. */
  label?: string
  className?: string
}

interface WorldShapes {
  land: GeoPermissibleObjects
  borders: GeoPermissibleObjects
}

const INK = '#14161A'
const PAPER = '#F4F5F7'
/** The whirl is air: it takes the cooling colour of the app. */
const AIR = '#2F7DF6'

/** Degrees of longitude travelled per second. */
const SPIN_SPEED = 32
const AXIAL_TILT = -18

/** Orbiting streaks: radius factor (of half-size), turns/second, arc length, phase. */
const WHIRL = [
  { radius: 0.78, speed: 0.55, sweep: 1.9, phase: 0, width: 1.6 },
  { radius: 0.86, speed: -0.38, sweep: 1.3, phase: 2.1, width: 1.2 },
  { radius: 0.94, speed: 0.27, sweep: 2.4, phase: 4.0, width: 0.9 },
] as const

let worldPromise: Promise<WorldShapes> | null = null

/** Country outlines (Natural Earth 1:110m), fetched once and code-split. */
function loadWorld(): Promise<WorldShapes> {
  if (!worldPromise) {
    worldPromise = Promise.all([
      import('topojson-client'),
      import('world-atlas/countries-110m.json'),
    ]).then(([topojson, atlas]) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const topology = (atlas.default ?? atlas) as any
      return {
        land: topojson.feature(topology, topology.objects.land) as GeoPermissibleObjects,
        borders: topojson.mesh(
          topology,
          topology.objects.countries,
          (a: unknown, b: unknown) => a !== b,
        ) as GeoPermissibleObjects,
      }
    })
  }
  return worldPromise
}

function drawWhirl(ctx: CanvasRenderingContext2D, half: number, seconds: number) {
  const SEGMENTS = 28
  ctx.lineCap = 'round'
  for (const streak of WHIRL) {
    const head = streak.phase + seconds * streak.speed * Math.PI * 2
    const direction = Math.sign(streak.speed)
    const radius = half * streak.radius
    // The tail is drawn as short segments whose opacity fades away from the head.
    for (let i = 0; i < SEGMENTS; i += 1) {
      const from = head - direction * (streak.sweep * (i + 1)) / SEGMENTS
      const to = head - direction * (streak.sweep * i) / SEGMENTS
      const strength = 1 - i / SEGMENTS
      ctx.beginPath()
      ctx.arc(half, half, radius, Math.min(from, to), Math.max(from, to))
      ctx.strokeStyle = AIR
      ctx.globalAlpha = 0.85 * strength * strength
      ctx.lineWidth = streak.width * (0.35 + 0.65 * strength)
      ctx.stroke()
    }
    ctx.globalAlpha = 0.9
    ctx.beginPath()
    ctx.arc(
      half + Math.cos(head) * radius,
      half + Math.sin(head) * radius,
      streak.width * 0.9,
      0,
      Math.PI * 2,
    )
    ctx.fillStyle = AIR
    ctx.fill()
  }
  ctx.globalAlpha = 1
}

function drawGlobe(
  ctx: CanvasRenderingContext2D,
  half: number,
  seconds: number,
  world: WorldShapes | null,
) {
  const radius = half * 0.62
  const projection = geoOrthographic()
    .translate([half, half])
    .scale(radius)
    .rotate([seconds * SPIN_SPEED, AXIAL_TILT])
    .clipAngle(90)
  const path = geoPath(projection, ctx)

  ctx.beginPath()
  path({ type: 'Sphere' })
  ctx.fillStyle = '#FFFFFF'
  ctx.fill()

  ctx.beginPath()
  path(geoGraticule10())
  ctx.strokeStyle = INK
  ctx.globalAlpha = 0.08
  ctx.lineWidth = 0.5
  ctx.stroke()
  ctx.globalAlpha = 1

  if (world) {
    ctx.beginPath()
    path(world.land)
    ctx.fillStyle = INK
    ctx.fill()

    ctx.beginPath()
    path(world.borders)
    ctx.strokeStyle = PAPER
    ctx.lineWidth = 0.4
    ctx.stroke()
  }

  ctx.beginPath()
  path({ type: 'Sphere' })
  ctx.strokeStyle = INK
  ctx.lineWidth = 1
  ctx.stroke()
}

/**
 * Monochrome spinning globe with real country outlines and a whirl of
 * orbiting streaks. Purely graphical: no visible text.
 */
export function GlobeLoader({ size = 200, label = 'Chargement', className = '' }: GlobeLoaderProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return

    const ratio = Math.min(window.devicePixelRatio || 1, 3)
    canvas.width = size * ratio
    canvas.height = size * ratio

    const reducedMotion =
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches

    let world: WorldShapes | null = null
    let frame = 0
    let cancelled = false
    const startedAt = performance.now()

    const render = (now: number) => {
      const seconds = reducedMotion ? 0 : (now - startedAt) / 1000
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0)
      ctx.clearRect(0, 0, size, size)
      drawWhirl(ctx, size / 2, seconds)
      drawGlobe(ctx, size / 2, seconds, world)
      if (!reducedMotion && !cancelled) frame = requestAnimationFrame(render)
    }

    render(startedAt)
    loadWorld()
      .then((shapes) => {
        world = shapes
        if (reducedMotion && !cancelled) render(startedAt)
      })
      .catch(() => {
        // Outlines are decorative: the bare sphere keeps spinning without them.
      })

    return () => {
      cancelled = true
      cancelAnimationFrame(frame)
    }
  }, [size])

  return (
    <div
      role="status"
      aria-label={label}
      className={`globe-loader ${className}`}
      style={{ width: size, height: size }}
      data-testid="globe-loader"
    >
      <canvas ref={canvasRef} aria-hidden style={{ width: size, height: size }} />
    </div>
  )
}
