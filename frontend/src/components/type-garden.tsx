import { useEffect, useRef } from 'react'

import { Garden } from '@/lib/type-garden'

type TypeGardenProps = {
  /** Word typed out on first load. May contain the mistake. */
  word?: string
  /** Word it corrects itself into once, at the end of the intro. */
  correction?: string
  className?: string
  /** Fired once the intro finishes and the CTA may be revealed. */
  onReady?: () => void
  /** Fired each frame with the Y offset (CSS px) where the CTA should sit. */
  onCtaOffset?: (y: number) => void
}

/**
 * Live "type garden" wordmark. Procedurally grows a unique plant from every
 * letter as it is typed. Double-tap the canvas to plant a rose.
 *
 * The engine is imperative canvas code, so it lives behind a ref and is torn
 * down on unmount (React 19 StrictMode mounts effects twice in dev).
 */
export function TypeGarden({
  word = 'ReSolve',
  correction,
  className,
  onReady,
  onCtaOffset,
}: TypeGardenProps) {
  const hostRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  // Keep the latest callbacks without forcing the garden to be rebuilt.
  // Refs must not be written during render, so sync after every commit.
  const readyRef = useRef(onReady)
  const offsetRef = useRef(onCtaOffset)
  useEffect(() => {
    readyRef.current = onReady
    offsetRef.current = onCtaOffset
  })

  useEffect(() => {
    const host = hostRef.current
    const canvas = canvasRef.current
    if (!host || !canvas) return

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    const garden = new Garden({
      canvas,
      host,
      word,
      correction,
      reducedMotion,
      onReady: () => readyRef.current?.(),
      onCtaOffset: (y) => offsetRef.current?.(y),
    })

    return () => garden.destroy()
  }, [word, correction])

  return (
    <div ref={hostRef} className={className} aria-hidden="true">
      <canvas ref={canvasRef} className="block h-full w-full" />
    </div>
  )
}
