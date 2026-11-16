import { GlobeLoader } from './GlobeLoader'

interface LoaderStageProps {
  /** Accessible description of what is loading (never shown on screen). */
  label: string
  className?: string
  testId?: string
}

/** Off-white stage with the globe loader centred in it. */
export function LoaderStage({ label, className = 'min-h-[320px]', testId }: LoaderStageProps) {
  return (
    <div className={`loader-stage ${className}`} data-testid={testId}>
      <GlobeLoader label={label} />
    </div>
  )
}
