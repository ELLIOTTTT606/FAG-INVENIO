import { useCallback, useRef, type ChangeEvent } from 'react'
import type { PlanAttachment } from '../api/generate'

interface Props {
  plans: PlanAttachment[]
  onChange: (plans: PlanAttachment[]) => void
  max?: number
}

const ACCEPTED_TYPES = ['image/png', 'image/jpeg', 'image/webp']
const ACCEPT_ATTR = 'image/png,image/jpeg,image/webp'

async function readAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(reader.error)
    reader.onload = () => resolve(String(reader.result ?? ''))
    reader.readAsDataURL(file)
  })
}

export function PlansUploader({ plans, onChange, max = 5 }: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const remaining = Math.max(0, max - plans.length)

  const handleFiles = useCallback(
    async (event: ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(event.target.files ?? [])
      event.target.value = ''
      if (!files.length) return
      const accepted = files
        .filter((f) => ACCEPTED_TYPES.includes(f.type))
        .slice(0, remaining)
      const added: PlanAttachment[] = await Promise.all(
        accepted.map(async (file) => ({
          name: file.name,
          dataUrl: await readAsDataUrl(file),
        })),
      )
      if (added.length) onChange([...plans, ...added])
    },
    [plans, onChange, remaining],
  )

  const remove = (index: number) => {
    onChange(plans.filter((_, i) => i !== index))
  }

  return (
    <div className="space-y-3" data-testid="plans-uploader">
      <div className="flex items-baseline justify-between">
        <h3 className="text-sm font-medium">Plans &amp; dimensions</h3>
        <span className="text-xs text-ink-muted">
          {plans.length} / {max}
        </span>
      </div>

      {plans.length > 0 ? (
        <ul className="grid grid-cols-2 gap-3 md:grid-cols-3">
          {plans.map((plan, index) => (
            <li
              key={`${plan.name}-${index}`}
              className="group relative overflow-hidden rounded-xl border border-ink-muted/15 bg-surface-light"
            >
              <img
                src={plan.dataUrl}
                alt={plan.name}
                className="aspect-video w-full bg-ink-muted/5 object-contain"
              />
              <div className="flex items-center justify-between gap-2 px-3 py-2 text-xs">
                <span className="truncate" title={plan.name}>
                  {plan.name}
                </span>
                <button
                  type="button"
                  onClick={() => remove(index)}
                  className="rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wider text-danger hover:bg-danger/10"
                  data-testid={`plans-remove-${index}`}
                  aria-label={`Retirer ${plan.name}`}
                >
                  Retirer
                </button>
              </div>
            </li>
          ))}
        </ul>
      ) : null}

      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={remaining === 0}
        className="w-full rounded-xl border-2 border-dashed border-ink-muted/30 px-4 py-6 text-sm text-ink-muted transition hover:border-accent hover:text-accent disabled:opacity-50"
        data-testid="plans-add"
      >
        {remaining === 0
          ? 'Limite atteinte'
          : 'Ajouter un plan (PNG / JPEG / WebP)'}
      </button>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPT_ATTR}
        onChange={handleFiles}
        className="hidden"
        data-testid="plans-input"
      />
    </div>
  )
}
