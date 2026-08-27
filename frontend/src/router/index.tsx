import { createBrowserRouter, type RouteObject } from 'react-router-dom'

import { AppLayout } from '@/components/AppLayout'
import { RequireAuth } from '@/components/RequireAuth'
import { DashboardPage } from '@/pages/DashboardPage'
import { LoginPage } from '@/pages/LoginPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { StorybookPage } from '@/pages/StorybookPage'
import { VehicleDetailPage } from '@/pages/VehicleDetailPage'
import { VehicleNewPage } from '@/pages/VehicleNewPage'
import { VehiclesPage } from '@/pages/VehiclesPage'

/**
 * Array separado (em vez de só o resultado de createBrowserRouter) pra os
 * testes de roteamento reaproveitarem a mesma estrutura via
 * createMemoryRouter, sem duplicar — e sem arriscar divergir de — a árvore
 * de rotas real.
 */
export const routes: RouteObject[] = [
  {
    // RequireAuth é layout route (Outlet) — decide uma vez se a árvore
    // inteira abaixo pode renderizar, em vez de embrulhar cada página.
    element: <RequireAuth />,
    children: [
      {
        // AppLayout também é layout route: header com usuário/logout/nav
        // fica montado uma vez, as páginas só trocam o conteúdo do Outlet.
        element: <AppLayout />,
        children: [
          { path: '/', element: <DashboardPage /> },
          { path: '/vehicles', element: <VehiclesPage /> },
          { path: '/vehicles/new', element: <VehicleNewPage /> },
          { path: '/vehicles/:id', element: <VehicleDetailPage /> },
        ],
      },
    ],
  },
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    // Página de teste do design system (Prompt 25) — não faz parte da
    // navegação real do produto, remover quando telas reais existirem.
    path: '/storybook',
    element: <StorybookPage />,
  },
  {
    path: '*',
    element: <NotFoundPage />,
  },
]

export const router = createBrowserRouter(routes)
