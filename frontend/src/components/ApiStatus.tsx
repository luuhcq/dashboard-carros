import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { useApiSchema } from '@/hooks/useApiSchema'

export function ApiStatus() {
  const { data, error, isPending } = useApiSchema()

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Conectividade com a API</CardTitle>
        <CardDescription>GET {import.meta.env.VITE_API_URL}/api/schema/</CardDescription>
      </CardHeader>
      <CardContent>
        {isPending && <p>Chamando o backend…</p>}
        {error && (
          <p className="text-destructive">
            Falha na chamada: {error.message}
          </p>
        )}
        {data && (
          <div>
            <p className="text-primary">Conexão OK — resposta recebida do backend.</p>
            <p>
              {data.info.title} v{data.info.version} (OpenAPI {data.openapi})
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
