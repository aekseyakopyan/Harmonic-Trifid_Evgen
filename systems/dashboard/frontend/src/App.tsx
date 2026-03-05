import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import LeadsFeedPage from './pages/LeadsFeedPage'
import LeadCardPage from './pages/LeadCardPage'
import DialogsPage from './pages/DialogsPage'
import DialogDetailPage from './pages/DialogDetailPage'
import PipelineConfigPage from './pages/PipelineConfigPage'
import AnalyticsPage from './pages/AnalyticsPage'
import PromptsPage from './pages/PromptsPage'
import PromptEditorPage from './pages/PromptEditorPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/leads" replace />} />
          <Route path="leads" element={<LeadsFeedPage />} />
          <Route path="leads/:id" element={<LeadCardPage />} />
          <Route path="dialogs" element={<DialogsPage />} />
          <Route path="dialogs/:id" element={<DialogDetailPage />} />
          <Route path="pipeline" element={<PipelineConfigPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="prompts" element={<PromptsPage />} />
          <Route path="prompts/new" element={<PromptEditorPage />} />
          <Route path="prompts/:id" element={<PromptEditorPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
