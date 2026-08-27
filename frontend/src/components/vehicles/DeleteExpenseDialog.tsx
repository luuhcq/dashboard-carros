import { Trash2 } from 'lucide-react'
import { useState } from 'react'
import type { MouseEvent } from 'react'
import { toast } from 'sonner'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useDeleteVehicleExpense } from '@/hooks/useDeleteVehicleExpense'
import type { VehicleExpense } from '@/types/expense'
import { formatCurrency } from '@/utils/formatCurrency'

export function DeleteExpenseDialog({
  vehicleId,
  expense,
}: {
  vehicleId: string
  expense: VehicleExpense
}) {
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')
  const [showMissingReasonError, setShowMissingReasonError] = useState(false)
  const deleteExpense = useDeleteVehicleExpense(vehicleId)

  const trimmedReason = reason.trim()

  function resetLocalState() {
    setReason('')
    setShowMissingReasonError(false)
  }

  // AlertDialogAction fecha o diálogo sozinho por padrão (comportamento do
  // Radix) — preventDefault() SEMPRE, e só chama setOpen(false) depois de
  // sucesso de verdade. Sem isso, um clique bloqueado no client (sem
  // justificativa) ou uma rejeição do backend fechariam o diálogo do mesmo
  // jeito, escondendo o erro.
  function handleConfirm(event: MouseEvent<HTMLButtonElement>) {
    event.preventDefault()

    if (!trimmedReason) {
      setShowMissingReasonError(true)
      return
    }

    deleteExpense.mutate(
      { expenseId: expense.id, deletionReason: trimmedReason },
      {
        onSuccess: () => {
          toast.success('Despesa excluída.')
          setOpen(false)
          resetLocalState()
        },
      },
    )
  }

  return (
    <AlertDialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (!next) resetLocalState()
      }}
    >
      <AlertDialogTrigger asChild>
        <Button variant="ghost" size="icon-sm" aria-label="Excluir despesa">
          <Trash2 />
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Excluir despesa?</AlertDialogTitle>
          <AlertDialogDescription>
            {expense.description} — {formatCurrency(expense.amount)}. Essa ação não pode ser
            desfeita.
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="deletion-reason" className="text-sm font-medium">
            Motivo da exclusão
          </label>
          <Textarea
            id="deletion-reason"
            rows={2}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
          {showMissingReasonError && !trimmedReason && (
            <p role="alert" className="text-sm text-destructive">
              Informe o motivo da exclusão.
            </p>
          )}
        </div>

        <AlertDialogFooter>
          <AlertDialogCancel>Cancelar</AlertDialogCancel>
          <AlertDialogAction onClick={handleConfirm} disabled={deleteExpense.isPending}>
            {deleteExpense.isPending ? 'Excluindo…' : 'Excluir'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
