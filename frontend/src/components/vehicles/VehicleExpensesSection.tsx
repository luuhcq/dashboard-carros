import type { ReactNode } from 'react'

import { DeleteExpenseDialog } from '@/components/vehicles/DeleteExpenseDialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useVehicleExpenses } from '@/hooks/useVehicleExpenses'
import type { VehicleDetail } from '@/types/vehicle'
import { EXPENSE_CATEGORY_LABELS } from '@/types/expense'
import { formatCurrency } from '@/utils/formatCurrency'
import { formatDate } from '@/utils/formatDate'

const COLUMN_COUNT = 7

function SkeletonRows() {
  return Array.from({ length: 3 }).map((_, rowIndex) => (
    <TableRow key={rowIndex}>
      {Array.from({ length: COLUMN_COUNT }).map((_, colIndex) => (
        <TableCell key={colIndex}>
          <Skeleton className="h-4 w-full max-w-20" />
        </TableCell>
      ))}
    </TableRow>
  ))
}

export function VehicleExpensesSection({ vehicle }: { vehicle: VehicleDetail }) {
  const {
    data: expenses,
    isPending,
    isError,
    refetch,
    isRefetching,
  } = useVehicleExpenses(vehicle.id)

  let body: ReactNode

  if (isPending) {
    body = <SkeletonRows />
  } else if (isError) {
    // Mesmo padrão de distinção erro-de-rede já usado em VehiclesTable/
    // DashboardSummaryCards/VehicleDetailPage.
    body = (
      <TableRow>
        <TableCell colSpan={COLUMN_COUNT} className="py-8 text-center">
          <div className="flex flex-col items-center gap-2">
            <p className="text-destructive">Não foi possível carregar as despesas.</p>
            <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isRefetching}>
              {isRefetching ? 'Tentando de novo…' : 'Tentar de novo'}
            </Button>
          </div>
        </TableCell>
      </TableRow>
    )
  } else if (!expenses || expenses.length === 0) {
    body = (
      <TableRow>
        <TableCell colSpan={COLUMN_COUNT} className="py-8 text-center text-muted-foreground">
          Nenhuma despesa registrada.
        </TableCell>
      </TableRow>
    )
  } else {
    body = expenses.map((expense) => (
      <TableRow key={expense.id}>
        <TableCell>{formatDate(expense.date)}</TableCell>
        <TableCell>{EXPENSE_CATEGORY_LABELS[expense.category]}</TableCell>
        <TableCell>{expense.description}</TableCell>
        <TableCell>{expense.supplier ?? '—'}</TableCell>
        <TableCell>{formatCurrency(expense.amount)}</TableCell>
        <TableCell>
          {expense.paid ? (
            <Badge className="border-transparent bg-success/10 text-success">Pago</Badge>
          ) : (
            <Badge variant="outline">Não pago</Badge>
          )}
        </TableCell>
        <TableCell>
          <DeleteExpenseDialog vehicleId={vehicle.id} expense={expense} />
        </TableCell>
      </TableRow>
    ))
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Custos</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Data</TableHead>
              <TableHead>Categoria</TableHead>
              <TableHead>Descrição</TableHead>
              <TableHead>Fornecedor</TableHead>
              <TableHead>Valor</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="sr-only">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>{body}</TableBody>
        </Table>

        {/* Vêm de vehicle.metrics (já buscado por VehicleDetailPage), nunca
            somados a partir da lista de despesas acima — duas fontes de
            verdade pro mesmo número seria exatamente o tipo de bug sutil
            que o prompt pediu pra evitar. */}
        <div className="mt-4 flex justify-end gap-8 border-t pt-4 text-sm">
          <div>
            <span className="text-muted-foreground">Total de despesas: </span>
            <span className="font-medium">{formatCurrency(vehicle.metrics.total_expenses)}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Custo total: </span>
            <span className="font-medium">{formatCurrency(vehicle.metrics.total_cost)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
