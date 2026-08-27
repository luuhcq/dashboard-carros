import { zodResolver } from '@hookform/resolvers/zod'
import { Controller, useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { ApiStatus } from '@/components/ApiStatus'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { formatCurrency } from '@/utils/formatCurrency'
import { formatDate } from '@/utils/formatDate'

// Linha do cenário do Prompt 12 (Honda Civic), um veículo ainda não vendido
// (null de verdade) e um cenário de prejuízo real (profit_per_day negativo) —
// pra provar visualmente que "-R$ 4.500,00" fica claro combinado com o token
// destructive, do mesmo jeito que success fica claro pro lucro.
const sampleVehicles = [
  {
    id: 1,
    model: 'Honda Civic',
    status: 'sold' as const,
    purchaseDate: '2026-01-05',
    saleDate: '2026-02-10',
    totalCost: '47300.00',
    profitPerDay: '158.33',
  },
  {
    id: 2,
    model: 'Toyota Corolla',
    status: 'in_stock' as const,
    purchaseDate: '2026-03-01',
    saleDate: null,
    totalCost: '52000.00',
    profitPerDay: null,
  },
  {
    id: 3,
    model: 'Fiat Uno',
    status: 'sold' as const,
    purchaseDate: '2026-01-10',
    saleDate: '2026-01-12',
    totalCost: '18000.00',
    profitPerDay: '-4500.00',
  },
]

function ProfitCell({ value }: { value: string | null }) {
  if (value == null) {
    return <TableCell className="text-muted-foreground">{formatCurrency(value)}</TableCell>
  }

  const isLoss = Number(value) < 0
  return (
    <TableCell className={isLoss ? 'font-medium text-destructive' : 'font-medium text-success'}>
      {formatCurrency(value)}
    </TableCell>
  )
}

const vehicleFormSchema = z.object({
  model: z.string().min(2, 'Informe o modelo do veículo.'),
  status: z.enum(['in_stock', 'sold'], { message: 'Selecione um status.' }),
  askingPrice: z.coerce
    .number({ message: 'Informe um preço válido.' })
    .positive('O preço precisa ser maior que zero.'),
})

// askingPrice usa z.coerce.number(), então o tipo de entrada do form (antes
// da coerção, o que o input HTML realmente produz) difere do tipo de saída
// (depois da coerção, o que o onSubmit recebe) — por isso os dois generics.
type VehicleFormInput = z.input<typeof vehicleFormSchema>
type VehicleFormOutput = z.output<typeof vehicleFormSchema>

function VehicleFormDemo() {
  const {
    control,
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<VehicleFormInput, unknown, VehicleFormOutput>({
    resolver: zodResolver(vehicleFormSchema),
  })

  const onSubmit = handleSubmit(() => {
    toast.success('Formulário validado com sucesso.')
  })

  return (
    <form onSubmit={onSubmit} className="max-w-sm" noValidate>
      <FieldGroup>
        <Field data-invalid={!!errors.model}>
          <FieldLabel htmlFor="model">Modelo</FieldLabel>
          <Input id="model" placeholder="Honda Civic" {...register('model')} />
          <FieldError errors={errors.model ? [errors.model] : undefined} />
        </Field>

        <Field data-invalid={!!errors.status}>
          <FieldLabel htmlFor="status">Status</FieldLabel>
          {/* Select do Radix não é um <input> nativo — precisa de Controller
              pra entrar no form state do RHF; register() sozinho (como no
              Form antigo tentava emular via ref) não funciona aqui. */}
          <Controller
            control={control}
            name="status"
            render={({ field }) => (
              <Select value={field.value} onValueChange={field.onChange}>
                <SelectTrigger id="status" className="w-full">
                  <SelectValue placeholder="Selecione o status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="in_stock">Em estoque</SelectItem>
                  <SelectItem value="sold">Vendido</SelectItem>
                </SelectContent>
              </Select>
            )}
          />
          <FieldError errors={errors.status ? [errors.status] : undefined} />
        </Field>

        <Field data-invalid={!!errors.askingPrice}>
          <FieldLabel htmlFor="askingPrice">Preço anunciado</FieldLabel>
          <Input
            id="askingPrice"
            type="number"
            step="0.01"
            placeholder="55000.00"
            {...register('askingPrice')}
          />
          <FieldError errors={errors.askingPrice ? [errors.askingPrice] : undefined} />
        </Field>

        <Button type="submit">Validar formulário</Button>
      </FieldGroup>
    </form>
  )
}

export function StorybookPage() {
  return (
    <main className="mx-auto flex max-w-4xl flex-col gap-8 p-8">
      <div>
        <h1 className="text-2xl font-semibold">Design system — página de teste</h1>
        <p className="text-muted-foreground">
          Validação visual dos componentes shadcn/ui sobre o tema navy/financeiro. Página
          temporária, não faz parte da navegação real do produto.
        </p>
      </div>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-medium">Conectividade com a API</h2>
        <ApiStatus />
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-medium">Buttons</h2>
        <div className="flex flex-wrap gap-2">
          <Button>Default</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="destructive">Destructive</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="link">Link</Button>
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-medium">Badges</h2>
        <div className="flex flex-wrap gap-2">
          <Badge>Default</Badge>
          <Badge variant="secondary">Secondary</Badge>
          <Badge variant="destructive">Destructive</Badge>
          <Badge variant="outline">Outline</Badge>
          <Badge className="border-transparent bg-success/10 text-success">Lucro</Badge>
          <Badge className="border-transparent bg-warning/15 text-warning-foreground">
            Estoque parado
          </Badge>
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-medium">Card</h2>
        <Card className="max-w-sm">
          <CardHeader>
            <CardTitle>Honda Civic</CardTitle>
            <CardDescription>Comprado em {formatDate(sampleVehicles[0].purchaseDate)}</CardDescription>
          </CardHeader>
          <CardContent>
            <p>Custo total: {formatCurrency(sampleVehicles[0].totalCost)}</p>
          </CardContent>
        </Card>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-medium">Table</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Modelo</TableHead>
              <TableHead>Compra</TableHead>
              <TableHead>Venda</TableHead>
              <TableHead>Custo total</TableHead>
              <TableHead>Lucro/dia</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sampleVehicles.map((vehicle) => (
              <TableRow key={vehicle.id}>
                <TableCell>{vehicle.model}</TableCell>
                <TableCell>{formatDate(vehicle.purchaseDate)}</TableCell>
                <TableCell>{formatDate(vehicle.saleDate)}</TableCell>
                <TableCell>{formatCurrency(vehicle.totalCost)}</TableCell>
                <ProfitCell value={vehicle.profitPerDay} />
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-medium">Tabs</h2>
        <Tabs defaultValue="stock" className="max-w-sm">
          <TabsList>
            <TabsTrigger value="stock">Em estoque</TabsTrigger>
            <TabsTrigger value="sold">Vendidos</TabsTrigger>
          </TabsList>
          <TabsContent value="stock">Toyota Corolla — {formatCurrency('52000.00')}</TabsContent>
          <TabsContent value="sold">Honda Civic — {formatCurrency('53000.00')}</TabsContent>
        </Tabs>
      </section>

      <section className="flex flex-wrap gap-3">
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline">Abrir dialog</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Editar veículo</DialogTitle>
              <DialogDescription>Exemplo de Dialog renderizando sobre o tema.</DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button>Salvar</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="destructive">Excluir veículo</Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Confirmar exclusão?</AlertDialogTitle>
              <AlertDialogDescription>Essa ação não pode ser desfeita.</AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction>Excluir</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="secondary">Ações</Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuLabel>Veículo</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Editar</DropdownMenuItem>
            <DropdownMenuItem>Duplicar</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <Button variant="outline" onClick={() => toast('Toast de teste disparado.')}>
          Disparar toast
        </Button>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-medium">Form (Field + React Hook Form + Zod)</h2>
        <VehicleFormDemo />
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-medium">Skeleton</h2>
        <div className="flex max-w-sm flex-col gap-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-24 w-full" />
        </div>
      </section>
    </main>
  )
}
