import { useEffect, useRef } from 'react'
import { prefersReducedMotion } from '../lib/motion'

const COLD = '#2F7DF6'
const WARM = '#FF7A3D'
const STREAKS = 70
const SEGMENTS = 10

interface Streak {
  x: number
  y: number
  speed: number
  warm: boolean
}

/** Height of the flow line passing through (x, y), all in 0..1 units. */
function flow(x: number, y: number, seconds: number): number {
  return y + Math.sin(x * 6 + seconds / 2.4 + y * 9) * 0.035
}

/**
 * Ambient layer behind the whole app: faint streamlines drifting left to
 * right, like air through a duct. Mostly cold blue, a few warm ones.
 */
export function AirflowBackground() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return

    const still = prefersReducedMotion()
    const streaks: Streak[] = Array.from({ length: STREAKS }, (_, i) => ({
      x: Math.random(),
      y: Math.random(),
      speed: 0.0005 + Math.random() * 0.0011,
      warm: i % 9 === 0,
    }))

    let width = 0
    let height = 0
    const resize = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 2)
      width = window.innerWidth
      height = window.innerHeight
      canvas.width = width * ratio
      canvas.height = height * ratio
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0)
    }
    resize()
    window.addEventListener('resize', resize)

    let frame = 0
    const draw = (now: number) => {
      const seconds = now / 1000
      ctx.clearRect(0, 0, width, height)
      ctx.lineWidth = 1
      ctx.lineCap = 'round'
      for (const streak of streaks) {
        const length = 0.08 + streak.speed * 60
        ctx.globalAlpha = 0.08 + streak.speed * 150
        ctx.strokeStyle = streak.warm ? WARM : COLD
        // A short curved trail that follows the flow line behind the head.
        ctx.beginPath()
        for (let i = 0; i <= SEGMENTS; i += 1) {
          const x = streak.x - (length * i) / SEGMENTS
          const px = x * width
          const py = flow(x, streak.y, seconds) * height
          if (i === 0) ctx.moveTo(px, py)
          else ctx.lineTo(px, py)
        }
        ctx.stroke()
        streak.x += streak.speed
        if (streak.x > 1.1) {
          streak.x = -0.02
          streak.y = Math.random()
        }
      }
      if (!still) frame = requestAnimationFrame(draw)
    }
    draw(0)

    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10 h-full w-full opacity-50"
    />
  )
}
