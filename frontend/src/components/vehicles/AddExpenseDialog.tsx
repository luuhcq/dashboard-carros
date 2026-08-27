import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import type { FieldPath } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useCreateVehicleExpense } from '@/hooks/useCreateVehicleExpense'
import type { ExpenseCategory, VehicleExpenseCreatePayload } from '@/types/expense'
import { EXPENSE_CATEGORY_LABELS, EXPENSE_CATEGORY_OPTIONS } from '@/types/expense'
import { applyServerFieldErrors } from '@/utils/applyServerFieldErrors'

const emptyToUndefined = (val: unknown) => (val === '' || val == null ? undefined : val)

const expenseFormSchema = z.object({
  date: z.string().min(1, 'Informe a data.'),
  category: z.enum(EXPENSE_CATEGORY_OPTIONS as [ExpenseCategory, ...ExpenseCategory[]], {
    message: 'Selecione uma categoria.',
  }),
  description: z.string().min(1, 'Informe a descrição.'),
  supplier: z.string().optional(),
  // Espelha o backend (MinValueValidator(0.01) no model): valor precisa
  // ser maior que zero, não só >= 0.
  amount: z.preprocess(
    emptyToUndefined,
    z.coerce
      .number({ message: 'Informe o valor.' })
      .positive('O valor precisa ser maior que zero.'),
  ),
  paid: z.boolean(),
})

type ExpenseFormInput = z.input<typeof expenseFormSchema>
type ExpenseFormOutput = z.output<typeof expenseFormSchema>

const FIELD_NAMES = Object.keys(expenseFormSchema.shape) as FieldPath<ExpenseFormInput>[]

function toPayload(values: ExpenseFormOutput): VehicleExpenseCreatePayload {
  return {
    date: values.date,
    category: values.category,
    description: values.description,
    supplier: values.supplier || undefined,
    amount: values.amount,
    paid: values.paid,
  }
}

export function AddExpenseDialog({ vehicleId }: { vehicleId: string }) {
  const [open, setOpen] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const createExpense = useCreateVehicleExpense(vehicleId)

  const {
    register,
    control,
    handleSubmit,
    reset,
    setError,
    formState: { errors },
  } = useForm<ExpenseFormInput, unknown, ExpenseFormOutput>({
    resolver: zodResolver(expenseFormSchema),
    // category começa em '' (não undefined) pra manter o Select do Radix
    // controlado desde o primeiro render — undefined causava o warning do
    // React "Select is changing from uncontrolled to controlled".
    defaultValues: { paid: false, category: '' as ExpenseCategory },
  })

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null)
    try {
      await createExpense.mutateAsync(toPayload(values))
      toast.success('Despesa adicionada.')
      reset({ paid: false, category: '' as ExpenseCategory })
      setOpen(false)
    } catch (error) {
      const leftover = applyServerFieldErrors(error, setError, FIELD_NAMES)
      if (leftover) setFormError(leftover)
    }
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>Adicionar despesa</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Adicionar despesa</DialogTitle>
        </DialogHeader>
        <form onSubmit={onSubmit} noValidate>
          <FieldGroup>
            {formError && (
              <p role="alert" className="text-sm text-destructive">
                {formError}
              </p>
            )}

            <Field data-invalid={!!errors.date}>
              <FieldLabel htmlFor="expense-date">Data</FieldLabel>
              <Input id="expense-date" type="date" {...register('date')} />
              <FieldError errors={errors.date ? [errors.date] : undefined} />
            </Field>

            <Field data-invalid={!!errors.category}>
              <FieldLabel htmlFor="expense-category">Categoria</FieldLabel>
              <Controller
                control={control}
                name="category"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger id="expense-category" className="w-full">
                      <SelectValue placeholder="Selecione a categoria" />
                    </SelectTrigger>
                    <SelectContent>
                      {EXPENSE_CATEGORY_OPTIONS.map((option) => (
                        <SelectItem key={option} value={option}>
                          {EXPENSE_CATEGORY_LABELS[option]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              <FieldError errors={errors.category ? [errors.category] : undefined} />
            </Field>

            <Field data-invalid={!!errors.description}>
              <FieldLabel htmlFor="expense-description">Descrição</FieldLabel>
              <Input id="expense-description" {...register('description')} />
              <FieldError errors={errors.description ? [errors.description] : undefined} />
            </Field>

            <Field data-invalid={!!errors.supplier}>
              <FieldLabel htmlFor="expense-supplier">Fornecedor</FieldLabel>
              <Input id="expense-supplier" {...register('supplier')} />
              <FieldError errors={errors.supplier ? [errors.supplier] : undefined} />
            </Field>

            <Field data-invalid={!!errors.amount}>
              <FieldLabel htmlFor="expense-amount">Valor</FieldLabel>
              <Input id="expense-amount" type="number" step="0.01" {...register('amount')} />
              <FieldError errors={errors.amount ? [errors.amount] : undefined} />
            </Field>

            <Field orientation="horizontal">
              <Controller
                control={control}
                name="paid"
                render={({ field }) => (
                  <Checkbox
                    id="expense-paid"
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  />
                )}
              />
              <FieldLabel htmlFor="expense-paid">Pago</FieldLabel>
            </Field>

            <DialogFooter>
              <Button type="submit" disabled={createExpense.isPending}>
                {createExpense.isPending ? 'Salvando…' : 'Adicionar despesa'}
              </Button>
            </DialogFooter>
          </FieldGroup>
        </form>
      </DialogContent>
    </Dialog>
  )
}
