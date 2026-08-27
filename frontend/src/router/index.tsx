import { createBrowserRouter } from 'react-router-dom'

import { RequireAuth } from '@/components/RequireAuth'
import { HomePage } from '@/pages/HomePage'
import { LoginPage } from '@/pages/LoginPage'
import { StorybookPage } from '@/pages/StorybookPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: (
      <RequireAuth>
        <HomePage />
      </RequireAuth>
    ),
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
])
