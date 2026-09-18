import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  GripVertical,
  RotateCcw,
  Save,
  Settings2,
} from 'lucide-react'
import {
  DndContext,
  closestCenter,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
  arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  getAdminPaymentProviders,
  reorderPaymentProviders,
  updatePaymentProvider,
  type PaymentProviderField,
  type PaymentProviderResponse,
  type PaymentProviderUpdateRequest,
} from '@/api/admin/payment-providers'
import { useTranslation } from 'react-i18next'
import { useToast } from '@/hooks/useToast'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const PROVIDER_DESCRIPTION_KEYS: Record<string, string> = {
  yookassa: 'admin_provider_desc_yookassa',
  freekassa: 'admin_provider_desc_freekassa',
  platega: 'admin_provider_desc_platega',
  severpay: 'admin_provider_desc_severpay',
  lavapay: 'admin_provider_desc_lavapay',
  stars: 'admin_provider_desc_stars',
  cryptopay: 'admin_provider_desc_cryptopay',
}

type DraftValue = string | number | boolean | null

interface SortableProviderRowProps {
  provider: PaymentProviderResponse
  index: number
  expanded: boolean
  onExpand: () => void
  onToggle: () => void
  disabled: boolean
}

function SortableProviderRow({ provider, index, expanded, onExpand, onToggle, disabled }: SortableProviderRowProps) {
  const { t } = useTranslation()
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: provider.id })

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.55 : 1, zIndex: isDragging ? 10 : undefined }}
      className="flex flex-wrap items-start gap-3 bg-[hsl(var(--card))] px-4 py-4 transition-colors hover:bg-[hsl(var(--muted)/0.3)] sm:flex-nowrap sm:items-center sm:gap-4 sm:px-5"
    >
      <button
        {...attributes}
        {...listeners}
        className="mt-1 cursor-grab touch-none rounded-md text-[hsl(var(--muted-foreground))] outline-none transition-colors hover:text-[hsl(var(--foreground))] focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))] sm:mt-0"
        aria-label={t('admin_drag_reorder')}
      >
        <GripVertical size={18} />
      </button>

      <span className="mt-1 w-5 select-none text-center text-xs tabular-nums text-[hsl(var(--muted-foreground))] sm:mt-0">{index + 1}</span>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="break-words font-semibold leading-snug text-[hsl(var(--foreground))]">{provider.display_name}</span>
          <span className="rounded bg-[hsl(var(--muted))] px-1.5 py-0.5 font-mono text-xs text-[hsl(var(--muted-foreground))]">{provider.provider_key}</span>
        </div>
        <p className="mt-1 max-w-3xl text-xs leading-relaxed text-[hsl(var(--muted-foreground))]">
          {PROVIDER_DESCRIPTION_KEYS[provider.provider_key] ? t(PROVIDER_DESCRIPTION_KEYS[provider.provider_key]) : ''}
        </p>
      </div>

      <div className="ml-8 flex w-[calc(100%-2rem)] shrink-0 items-center justify-between gap-2 sm:ml-0 sm:w-auto sm:flex-row">
        <Badge variant={provider.is_configured ? 'success' : 'warning'} dot>
          {provider.is_configured ? 'Настроен' : 'Нужны данные'}
        </Badge>
        <Button type="button" variant="outline" size="sm" onClick={onExpand} aria-expanded={expanded} className="gap-1.5">
          <Settings2 size={14} />
          <span className="hidden md:inline">Настроить</span>
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </Button>
        <div className="flex items-center gap-2">
          <Badge variant={provider.is_enabled ? 'success' : 'secondary'} dot>
            {provider.is_enabled ? t('admin_enabled') : t('admin_disabled')}
          </Badge>
          <Switch
            checked={provider.is_enabled}
            onCheckedChange={onToggle}
            disabled={disabled}
            aria-label={`${provider.display_name}: ${provider.is_enabled ? t('admin_enabled') : t('admin_disabled')}`}
          />
        </div>
      </div>
    </div>
  )
}

function ProviderFieldInput({ field, value, cleared, onChange, onClear }: {
  field: PaymentProviderField
  value: DraftValue | undefined
  cleared: boolean
  onChange: (value: DraftValue) => void
  onClear: () => void
}) {
  if (field.kind === 'boolean') {
    return (
      <div className="flex min-h-10 items-center gap-3">
        <Switch checked={Boolean(value)} onCheckedChange={onChange} aria-label={field.label} />
        <span className="text-sm text-[hsl(var(--muted-foreground))]">{value ? 'Включено' : 'Выключено'}</span>
      </div>
    )
  }

  if (field.kind === 'select') {
    return (
      <select
        value={value == null ? '' : String(value)}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 w-full rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))] px-3 text-base outline-none transition-shadow focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))] sm:text-sm"
      >
        <option value="">По умолчанию</option>
        {field.options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
    )
  }

  const inputType = field.secret ? 'password' : field.kind === 'number' ? 'number' : field.kind
  const placeholder = field.secret && field.is_set && !cleared ? 'Сохранено — введите только для замены' : undefined

  return (
    <div className="flex gap-2">
      <div className="min-w-0 flex-1">
        <Input
          type={inputType}
          value={value == null ? '' : String(value)}
          min={field.minimum ?? undefined}
          max={field.maximum ?? undefined}
          placeholder={placeholder}
          autoComplete={field.secret ? 'new-password' : 'off'}
          onChange={(event) => onChange(event.target.value)}
          className="min-w-0 text-base sm:text-sm"
        />
      </div>
      {field.secret && field.is_set && (
        <Button type="button" variant="outline" size="sm" onClick={onClear} className="h-10 shrink-0">
          <RotateCcw size={14} className="mr-1.5" />
          {cleared ? 'Вернуть' : 'Удалить'}
        </Button>
      )}
    </div>
  )
}

function ProviderSettingsPanel({ provider, saving, onSave }: {
  provider: PaymentProviderResponse
  saving: boolean
  onSave: (body: PaymentProviderUpdateRequest) => void
}) {
  const [displayName, setDisplayName] = useState(provider.display_name)
  const [draft, setDraft] = useState<Record<string, DraftValue>>({})
  const [clearedSecrets, setClearedSecrets] = useState<Set<string>>(new Set())

  useEffect(() => {
    setDisplayName(provider.display_name)
    setDraft(Object.fromEntries(provider.fields.filter((field) => !field.secret).map((field) => [field.key, field.value])))
    setClearedSecrets(new Set())
  }, [provider])

  const fieldLabels = useMemo(() => Object.fromEntries(provider.fields.map((field) => [field.key, field.label])), [provider.fields])

  const submit = () => {
    const config: Record<string, DraftValue> = {}
    for (const field of provider.fields) {
      if (!field.secret) config[field.key] = draft[field.key] ?? null
      else if (clearedSecrets.has(field.key)) config[field.key] = null
      else if (draft[field.key] != null && String(draft[field.key]).trim() !== '') config[field.key] = draft[field.key]!
    }
    onSave({ display_name: displayName, config })
  }

  return (
    <div className="border-t border-[hsl(var(--border))] bg-[hsl(var(--muted)/0.18)] px-4 py-5 sm:px-12 sm:py-6">
      <div className="max-w-4xl space-y-5">
        <div>
          <h2 className="text-base font-semibold">Настройки {provider.provider_key}</h2>
          <p className="mt-1 text-sm leading-relaxed text-[hsl(var(--muted-foreground))]">
            Название увидит пользователь. Секреты зашифрованы в базе и после сохранения не отображаются.
          </p>
        </div>

        {!provider.is_configured && provider.missing_fields.length > 0 && (
          <Alert variant="warning" icon={<AlertTriangle size={16} />}>
            Заполните обязательные поля: {provider.missing_fields.map((key) => fieldLabels[key] ?? key).join(', ')}.
          </Alert>
        )}

        <div className="grid gap-4 md:grid-cols-2">
          <label className="min-w-0 md:col-span-2">
            <span className="mb-1.5 block text-sm font-medium">Название для пользователя</span>
            <Input value={displayName} maxLength={100} onChange={(event) => setDisplayName(event.target.value)} className="text-base sm:text-sm" />
          </label>

          {provider.fields.map((field) => (
            <label key={field.key} className="min-w-0">
              <span className="mb-1.5 flex flex-wrap items-center gap-1.5 text-sm font-medium">
                {field.label}
                {field.required && <span className="text-[var(--danger)]" aria-label="обязательное поле">*</span>}
                {field.secret && field.is_set && !clearedSecrets.has(field.key) && (
                  <span className="inline-flex items-center gap-1 text-xs font-normal text-[var(--success)]"><CheckCircle2 size={12} /> сохранено</span>
                )}
              </span>
              <ProviderFieldInput
                field={field}
                value={draft[field.key]}
                cleared={clearedSecrets.has(field.key)}
                onChange={(value) => {
                  setDraft((current) => ({ ...current, [field.key]: value }))
                  if (field.secret) setClearedSecrets((current) => {
                    const next = new Set(current)
                    next.delete(field.key)
                    return next
                  })
                }}
                onClear={() => {
                  setDraft((current) => ({ ...current, [field.key]: '' }))
                  setClearedSecrets((current) => {
                    const next = new Set(current)
                    if (next.has(field.key)) next.delete(field.key)
                    else next.add(field.key)
                    return next
                  })
                }}
              />
              {field.help && <span className="mt-1 block text-xs leading-relaxed text-[hsl(var(--muted-foreground))]">{field.help}</span>}
            </label>
          ))}
        </div>

        <div className="flex justify-end">
          <Button type="button" onClick={submit} disabled={saving || displayName.trim().length === 0} className="min-w-36">
            <Save size={15} className="mr-2" />
            {saving ? 'Сохраняем…' : 'Сохранить'}
          </Button>
        </div>
      </div>
    </div>
  )
}

export function PaymentProvidersPage() {
  const qc = useQueryClient()
  const { t } = useTranslation()
  const toast = useToast()
  const [localOrder, setLocalOrder] = useState<number[] | null>(null)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin', 'payment-providers'],
    queryFn: getAdminPaymentProviders,
    select: (response) => response.items,
  })

  const updateMut = useMutation({
    mutationFn: ({ id, body }: { id: number; body: PaymentProviderUpdateRequest }) => updatePaymentProvider(id, body),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['admin', 'payment-providers'] })
      toast.success('Настройки провайдера сохранены')
    },
    onError: (error: Error) => toast.error(error.message || 'Не удалось сохранить настройки'),
  })

  const reorderMut = useMutation({
    mutationFn: reorderPaymentProviders,
    onSuccess: async () => {
      setLocalOrder(null)
      await qc.invalidateQueries({ queryKey: ['admin', 'payment-providers'] })
    },
    onError: (error: Error) => {
      setLocalOrder(null)
      toast.error(error.message || 'Не удалось сохранить порядок')
    },
  })

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const providers = useMemo(() => {
    if (!data) return []
    if (!localOrder) return data
    return [...data].sort((a, b) => localOrder.indexOf(a.id) - localOrder.indexOf(b.id))
  }, [data, localOrder])

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const ids = providers.map((provider) => provider.id)
    const reordered = arrayMove(ids, ids.indexOf(active.id as number), ids.indexOf(over.id as number))
    setLocalOrder(reordered)
    reorderMut.mutate(reordered)
  }

  return (
    <div className="space-y-6 px-4 py-6 sm:p-8">
      <div>
        <h1 className="text-2xl font-bold text-[hsl(var(--foreground))]">{t('admin_providers_title')}</h1>
        <p className="mt-1 max-w-3xl text-sm leading-relaxed text-[hsl(var(--muted-foreground))]">
          Названия, порядок, доступность и все реквизиты провайдеров управляются здесь. Изменения применяются к сайту сразу, к боту — в течение нескольких секунд.
        </p>
      </div>

      {isLoading && (
        <div className="space-y-3" aria-label="Загрузка провайдеров">
          {[...Array(7)].map((_, index) => <div key={index} className="h-20 animate-pulse rounded-xl bg-[hsl(var(--muted))]" />)}
        </div>
      )}

      {isError && (
        <Card>
          <CardContent className="flex flex-col items-start gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-[hsl(var(--muted-foreground))]">{t('admin_providers_load_error')}</p>
            <Button type="button" variant="outline" size="sm" onClick={() => refetch()}>Повторить</Button>
          </CardContent>
        </Card>
      )}

      {providers.length > 0 && (
        <Card className="overflow-hidden">
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={providers.map((provider) => provider.id)} strategy={verticalListSortingStrategy}>
              <div className="divide-y divide-[hsl(var(--border))]">
                {providers.map((provider, index) => (
                  <div key={provider.id}>
                    <SortableProviderRow
                      provider={provider}
                      index={index}
                      expanded={expandedId === provider.id}
                      onExpand={() => setExpandedId((current) => current === provider.id ? null : provider.id)}
                      onToggle={() => updateMut.mutate({ id: provider.id, body: { is_enabled: !provider.is_enabled } })}
                      disabled={updateMut.isPending || reorderMut.isPending}
                    />
                    {expandedId === provider.id && (
                      <ProviderSettingsPanel
                        provider={provider}
                        saving={updateMut.isPending}
                        onSave={(body) => updateMut.mutate({ id: provider.id, body })}
                      />
                    )}
                  </div>
                ))}
              </div>
            </SortableContext>
          </DndContext>
        </Card>
      )}

      <Alert variant="info">
        Провайдер нельзя включить, пока не заполнены обязательные реквизиты. Отключённые способы оплаты и их цены не показываются пользователю.
      </Alert>
    </div>
  )
}
