import { cn } from '@/lib/utils'

export interface PublicPaymentProvider {
  key: string
  display_name: string
}

interface PaymentMethodGridProps {
  providers: PublicPaymentProvider[]
  selectedProvider: string | null
  onSelect: (provider: string) => void
  disabled?: boolean
}

export function PaymentMethodGrid({
  providers,
  selectedProvider,
  onSelect,
  disabled,
}: PaymentMethodGridProps) {
  if (providers.length === 0) {
    return (
      <p className="text-sm text-[hsl(var(--muted-foreground))]">
        Нет доступных способов оплаты
      </p>
    )
  }

  return (
    <div className="flex flex-wrap gap-2">
      {providers.map((provider) => (
        <button
          key={provider.key}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(provider.key)}
          className={cn(
            'flex items-center gap-2 rounded-[10px] border px-4 py-2.5 text-sm font-medium transition-all whitespace-nowrap',
            'hover:border-[color-mix(in_srgb,hsl(var(--primary))_50%,transparent)] hover:bg-[var(--primary-soft)]',
            selectedProvider === provider.key
              ? 'border-[hsl(var(--primary))] bg-[var(--primary-soft)] ring-2 ring-inset ring-[color-mix(in_srgb,hsl(var(--primary))_35%,transparent)]'
              : 'border-[hsl(var(--border))] bg-[hsl(var(--card))]',
            disabled && 'opacity-50 cursor-not-allowed',
          )}
        >
          {provider.display_name}
        </button>
      ))}
    </div>
  )
}
