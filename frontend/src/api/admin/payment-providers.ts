import { apiRequest } from '@/api/client'

export interface PaymentProviderResponse {
  id: number
  provider_key: string
  display_name: string
  is_enabled: boolean
  sort_order: number
  is_configured: boolean
  missing_fields: string[]
  fields: PaymentProviderField[]
  updated_at: string | null
}

export interface PaymentProviderField {
  key: string
  label: string
  kind: 'text' | 'password' | 'number' | 'url' | 'email' | 'boolean' | 'select'
  required: boolean
  secret: boolean
  help: string | null
  options: Array<{ value: string; label: string }>
  minimum: number | null
  maximum: number | null
  value: string | number | boolean | null
  is_set: boolean
}

export interface PaymentProvidersListResponse {
  items: PaymentProviderResponse[]
}

export interface PaymentProviderUpdateRequest {
  is_enabled?: boolean
  display_name?: string
  config?: Record<string, string | number | boolean | null>
}

export function reorderPaymentProviders(providerIds: number[]): Promise<PaymentProvidersListResponse> {
  return apiRequest<PaymentProvidersListResponse>('/admin/payment-providers/order', {
    method: 'PUT',
    body: JSON.stringify({ provider_ids: providerIds }),
  })
}

export function getAdminPaymentProviders(): Promise<PaymentProvidersListResponse> {
  return apiRequest<PaymentProvidersListResponse>('/admin/payment-providers')
}

export function updatePaymentProvider(
  providerId: number,
  body: PaymentProviderUpdateRequest,
): Promise<PaymentProviderResponse> {
  return apiRequest<PaymentProviderResponse>(`/admin/payment-providers/${providerId}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}
