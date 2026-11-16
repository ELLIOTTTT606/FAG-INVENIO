import { useEffect, useState } from 'react'
import { flushSync } from 'react-dom'

/** True when animations should be skipped (user preference, or no media queries at all). */
export function prefersReducedMotion(): boolean {
  return (
    typeof window === 'undefined' ||
    typeof window.matchMedia !== 'function' ||
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

type ViewTransitionDocument = Document & {
  startViewTransition?: (update: () => void) => unknown
}

/**
 * Applies a state change inside a View Transition, so elements sharing a
 * `view-transition-name` morph from their old box to their new one. Falls
 * back to a plain update where the API or motion is unavailable.
 */
export function withViewTransition(update: () => void): void {
  const doc = document as ViewTransitionDocument
  if (prefersReducedMotion() || typeof doc.startViewTransition !== 'function') {
    update()
    return
  }
  doc.startViewTransition(() => flushSync(update))
}

/** Animates from 0 to `target` once; returns `target` straight away without motion. */
export function useCountUp(target: number, durationMs = 1000, delayMs = 250): number {
  const [value, setValue] = useState(() => (prefersReducedMotion() ? target : 0))

  useEffect(() => {
    if (prefersReducedMotion()) {
      setValue(target)
      return
    }
    let frame = 0
    let start: number | null = null
    const step = (now: number) => {
      if (start === null) start = now + delayMs
      const progress = Math.min(Math.max((now - start) / durationMs, 0), 1)
      setValue(target * (1 - Math.pow(1 - progress, 4)))
      if (progress < 1) frame = requestAnimationFrame(step)
    }
    frame = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame)
  }, [target, durationMs, delayMs])

  return value
}
