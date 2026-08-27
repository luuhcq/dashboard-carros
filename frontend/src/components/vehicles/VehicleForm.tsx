import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import type { FieldPath } from 'react-hook-form'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
  FieldLegend,
  FieldSet,
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import type { VehicleCreatePayload, VehicleUpdatePayload } from '@/types/vehicle'
import { applyServerFieldErrors } from '@/utils/applyServerFieldErrors'
import { formatCurrency } from '@/utils/formatCurrency'

const CURRENT_YEAR = new Date().getFullYear()

// Converte "" (input vazio) em undefined antes do coerce — sem isso,
// Number('') vira 0 e um campo opcional em branco seria enviado como "0",
// não como ausente.
const emptyToUndefined = (val: unknown) => (val === '' || val == null ? undefined : val)

function optionalYear(label: string) {
  return z.preprocess(
    emptyToUndefined,
    z.coerce
      .number({ message: `${label} inválido.` })
      .int(`${label} inválido.`)
      // Faixa decidida no frontend (1900–ano atual+1) — o backend não impõe
      // limite nenhum aqui (PositiveSmallIntegerField só garante >= 0), só
      // conveniência de UI pra pegar erro de digitação óbvio.
      .min(1900, `${label} precisa ser 1900 ou depois.`)
      .max(CURRENT_YEAR + 1, `${label} não pode ser depois de ${CURRENT_YEAR + 1}.`)
      .optional(),
  )
}

function optionalNonNegativeInt(message: string) {
  return z.preprocess(
    emptyToUndefined,
    z.coerce.number({ message }).int(message).min(0, message).optional(),
  )
}

function optionalNonNegativeMoney(message: string) {
  return z.preprocess(emptyToUndefined, z.coerce.number({ message }).min(0, message).optional())
}

// status não faz parte deste formulário de propósito (decisão do Prompt
// 30, mantida na edição pelo Prompt 31 por consistência): todo veículo
// novo nasce PURCHASED, default do model. status=SOLD é bloqueado nesse
// mesmo endpoint tanto no create quanto no PATCH — expor um Select
// obrigaria excluir SOLD manualmente da lista só pra oferecer transições
// de status que são um fluxo próprio, fora de escopo deste prompt.
const vehicleFormSchema = z.object({
  brand: z.string().min(1, 'Informe a marca.'),
  model: z.string().min(1, 'Informe o modelo.'),
  version: z.string().optional(),
  manufacture_year: optionalYear('Ano de fabricação'),
  model_year: optionalYear('Ano do modelo'),
  mileage: optionalNonNegativeInt('Quilometragem não pode ser negativa.'),
  plate: z.string().optional(),
  chassis: z.string().optional(),
  color: z.string().optional(),
  source: z.string().optional(),
  supplier_name: z.string().optional(),
  purchase_date: z.string().min(1, 'Informe a data de compra.'),
  // Só valida >= 0 de propósito — não valida casas decimais aqui: é
  // exatamente o tipo de regra que o backend aplica (DecimalField,
  // decimal_places=2) e que o client não replica, então um erro desses
  // chega via applyServerFieldErrors, não fica escondido atrás de uma
  // validação client-side "ajudando demais".
  purchase_price: z.preprocess(
    emptyToUndefined,
    z.coerce
      .number({ message: 'Informe o preço de compra.' })
      .min(0, 'Preço de compra não pode ser negativo.'),
  ),
  fipe_reference_value: optionalNonNegativeMoney('Valor FIPE não pode ser negativo.'),
  fipe_code: z.string().optional(),
  notes: z.string().optional(),
})

type VehicleFormInput = z.input<typeof vehicleFormSchema>
type VehicleFormOutput = z.output<typeof vehicleFormSchema>

const FIELD_NAMES = Object.keys(vehicleFormSchema.shape) as FieldPath<VehicleFormInput>[]

function toWritableFields(values: VehicleFormOutput): VehicleCreatePayload {
  return {
    brand: values.brand,
    model: values.model,
    version: values.version || undefined,
    manufacture_year: values.manufacture_year,
    model_year: values.model_year,
    mileage: values.mileage,
    plate: values.plate || undefined,
    chassis: values.chassis || undefined,
    color: values.color || undefined,
    source: values.source || undefined,
    supplier_name: values.supplier_name || undefined,
    purchase_date: values.purchase_date,
    purchase_price: values.purchase_price,
    fipe_reference_value: values.fipe_reference_value,
    fipe_code: values.fipe_code || undefined,
    notes: values.notes || undefined,
  }
}

/** Só os campos que o usuário de fato tocou (RHF dirtyFields) — PATCH
 * parcial de verdade, nunca reenvia o formulário inteiro na edição. */
function pickDirtyFields(
  payload: VehicleCreatePayload,
  dirtyFields: Partial<Record<keyof VehicleCreatePayload, unknown>>,
): VehicleUpdatePayload {
  const result: VehicleUpdatePayload = {}
  for (const key of Object.keys(payload) as (keyof VehicleCreatePayload)[]) {
    if (dirtyFields[key]) {
      // TS não consegue provar que o tipo de payload[key] casa com o
      // campo correspondente de result sem essa asserção — key vem do
      // mesmo objeto payload em ambos os lados.
      ;(result as Record<string, unknown>)[key] = payload[key]
    }
  }
  return result
}

interface PricingInfo {
  askingPrice: string | null
  salePrice: string | null
}

interface VehicleFormProps {
  mode: 'create' | 'edit'
  defaultValues?: Partial<VehicleFormInput>
  /** Só em modo edit — mostrado como texto, nunca como campo editável. */
  pricingInfo?: PricingInfo
  isSubmitting: boolean
  submitLabel: string
  /** Deve rejeitar com o ApiError original em caso de falha — VehicleForm
   * mapeia isso pros campos certos via applyServerFieldErrors. */
  onSubmit: (payload: VehicleCreatePayload | VehicleUpdatePayload) => Promise<unknown>
}

export function VehicleForm({
  mode,
  defaultValues,
  pricingInfo,
  isSubmitting,
  submitLabel,
  onSubmit,
}: VehicleFormProps) {
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, dirtyFields, isDirty },
  } = useForm<VehicleFormInput, unknown, VehicleFormOutput>({
    resolver: zodResolver(vehicleFormSchema),
    defaultValues,
  })

  const onFormSubmit = handleSubmit(async (values) => {
    setFormError(null)
    const fullPayload = toWritableFields(values)
    const payload = mode === 'edit' ? pickDirtyFields(fullPayload, dirtyFields) : fullPayload

    try {
      await onSubmit(payload)
    } catch (error) {
      const leftover = applyServerFieldErrors(error, setError, FIELD_NAMES)
      if (leftover) setFormError(leftover)
    }
  })

  const submitDisabled = isSubmitting || (mode === 'edit' && !isDirty)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Dados do veículo</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={onFormSubmit} noValidate>
          <FieldGroup>
            {mode === 'edit' && pricingInfo && (
              <div className="rounded-lg border bg-muted/30 p-4">
                <p className="text-sm font-medium">Preço de venda</p>
                <div className="mt-2 grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">Preço pedido: </span>
                    <span className="font-medium">{formatCurrency(pricingInfo.askingPrice)}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Preço de venda: </span>
                    <span className="font-medium">{formatCurrency(pricingInfo.salePrice)}</span>
                  </div>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  Esses valores não são editados por aqui. Gerencie o preço pela página de
                  detalhe do veículo.
                </p>
              </div>
            )}

            {formError && (
              <p role="alert" className="text-sm text-destructive">
                {formError}
              </p>
            )}

            <FieldSet>
              <FieldLegend>Identificação</FieldLegend>
              <FieldGroup>
                <div className="grid grid-cols-2 gap-4">
                  <Field data-invalid={!!errors.brand}>
                    <FieldLabel htmlFor="brand">Marca</FieldLabel>
                    <Input id="brand" {...register('brand')} />
                    <FieldError errors={errors.brand ? [errors.brand] : undefined} />
                  </Field>
                  <Field data-invalid={!!errors.model}>
                    <FieldLabel htmlFor="model">Modelo</FieldLabel>
                    <Input id="model" {...register('model')} />
                    <FieldError errors={errors.model ? [errors.model] : undefined} />
                  </Field>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <Field data-invalid={!!errors.version}>
                    <FieldLabel htmlFor="version">Versão</FieldLabel>
                    <Input id="version" {...register('version')} />
                    <FieldError errors={errors.version ? [errors.version] : undefined} />
                  </Field>
                  <Field data-invalid={!!errors.color}>
                    <FieldLabel htmlFor="color">Cor</FieldLabel>
                    <Input id="color" {...register('color')} />
                    <FieldError errors={errors.color ? [errors.color] : undefined} />
                  </Field>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <Field data-invalid={!!errors.plate}>
                    <FieldLabel htmlFor="plate">Placa</FieldLabel>
                    <Input id="plate" {...register('plate')} />
                    <FieldError errors={errors.plate ? [errors.plate] : undefined} />
                  </Field>
                  <Field data-invalid={!!errors.chassis}>
                    <FieldLabel htmlFor="chassis">Chassi</FieldLabel>
                    <Input id="chassis" {...register('chassis')} />
                    <FieldError errors={errors.chassis ? [errors.chassis] : undefined} />
                  </Field>
                </div>
              </FieldGroup>
            </FieldSet>

            <FieldSet>
              <FieldLegend>Ano e quilometragem</FieldLegend>
              <FieldGroup>
                <div className="grid grid-cols-3 gap-4">
                  <Field data-invalid={!!errors.manufacture_year}>
                    <FieldLabel htmlFor="manufacture_year">Ano fabricação</FieldLabel>
                    <Input id="manufacture_year" type="number" {...register('manufacture_year')} />
                    <FieldError
                      errors={errors.manufacture_year ? [errors.manufacture_year] : undefined}
                    />
                  </Field>
                  <Field data-invalid={!!errors.model_year}>
                    <FieldLabel htmlFor="model_year">Ano modelo</FieldLabel>
                    <Input id="model_year" type="number" {...register('model_year')} />
                    <FieldError errors={errors.model_year ? [errors.model_year] : undefined} />
                  </Field>
                  <Field data-invalid={!!errors.mileage}>
                    <FieldLabel htmlFor="mileage">Quilometragem</FieldLabel>
                    <Input id="mileage" type="number" {...register('mileage')} />
                    <FieldError errors={errors.mileage ? [errors.mileage] : undefined} />
                  </Field>
                </div>
              </FieldGroup>
            </FieldSet>

            <FieldSet>
              <FieldLegend>Compra</FieldLegend>
              <FieldGroup>
                <div className="grid grid-cols-2 gap-4">
                  <Field data-invalid={!!errors.purchase_date}>
                    <FieldLabel htmlFor="purchase_date">Data da compra</FieldLabel>
                    <Input id="purchase_date" type="date" {...register('purchase_date')} />
                    <FieldError
                      errors={errors.purchase_date ? [errors.purchase_date] : undefined}
                    />
                  </Field>
                  <Field data-invalid={!!errors.purchase_price}>
                    <FieldLabel htmlFor="purchase_price">Preço de compra</FieldLabel>
                    <Input
                      id="purchase_price"
                      type="number"
                      step="0.01"
                      {...register('purchase_price')}
                    />
                    <FieldError
                      errors={errors.purchase_price ? [errors.purchase_price] : undefined}
                    />
                  </Field>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <Field data-invalid={!!errors.source}>
                    <FieldLabel htmlFor="source">Origem</FieldLabel>
                    <Input id="source" {...register('source')} />
                    <FieldError errors={errors.source ? [errors.source] : undefined} />
                  </Field>
                  <Field data-invalid={!!errors.supplier_name}>
                    <FieldLabel htmlFor="supplier_name">Fornecedor</FieldLabel>
                    <Input id="supplier_name" {...register('supplier_name')} />
                    <FieldError
                      errors={errors.supplier_name ? [errors.supplier_name] : undefined}
                    />
                  </Field>
                </div>
              </FieldGroup>
            </FieldSet>

            <FieldSet>
              <FieldLegend>FIPE</FieldLegend>
              <FieldGroup>
                <div className="grid grid-cols-2 gap-4">
                  <Field data-invalid={!!errors.fipe_reference_value}>
                    <FieldLabel htmlFor="fipe_reference_value">Valor de referência</FieldLabel>
                    <Input
                      id="fipe_reference_value"
                      type="number"
                      step="0.01"
                      {...register('fipe_reference_value')}
                    />
                    <FieldError
                      errors={
                        errors.fipe_reference_value ? [errors.fipe_reference_value] : undefined
                      }
                    />
                  </Field>
                  <Field data-invalid={!!errors.fipe_code}>
                    <FieldLabel htmlFor="fipe_code">Código FIPE</FieldLabel>
                    <Input id="fipe_code" {...register('fipe_code')} />
                    <FieldError errors={errors.fipe_code ? [errors.fipe_code] : undefined} />
                  </Field>
                </div>
              </FieldGroup>
            </FieldSet>

            <Field data-invalid={!!errors.notes}>
              <FieldLabel htmlFor="notes">Observações</FieldLabel>
              <Textarea id="notes" rows={3} {...register('notes')} />
              <FieldError errors={errors.notes ? [errors.notes] : undefined} />
            </Field>

            <Button type="submit" disabled={submitDisabled}>
              {isSubmitting ? 'Salvando…' : submitLabel}
            </Button>
          </FieldGroup>
        </form>
      </CardContent>
    </Card>
  )
}
