import { createBrowserRouter } from 'react-router-dom'

import { HomePage } from '@/pages/HomePage'
import { StorybookPage } from '@/pages/StorybookPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <HomePage />,
  },
  {
    // Página de teste do design system (Prompt 25) — não faz parte da
    // navegação real do produto, remover quando telas reais existirem.
    path: '/storybook',
    element: <StorybookPage />,
  },
])
