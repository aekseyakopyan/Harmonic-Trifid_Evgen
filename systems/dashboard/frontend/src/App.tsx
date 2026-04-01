import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import LeadsFeedPage from './pages/LeadsFeedPage'
import LeadCardPage from './pages/LeadCardPage'
import DialogsPage from './pages/DialogsPage'
import DialogDetailPage from './pages/DialogDetailPage'
import PipelineConfigPage from './pages/PipelineConfigPage'
import AnalyticsPage from './pages/AnalyticsPage'
import PromptsPage from './pages/PromptsPage'
import PromptEditorPage from './pages/PromptEditorPage'
import FilterStatsPage from './pages/FilterStatsPage'
import GuidePage from './pages/GuidePage'
import VacanciesPage from './pages/VacanciesPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="leads" element={<LeadsFeedPage />} />
          <Route path="leads/:id" element={<LeadCardPage />} />
          <Route path="dialogs" element={<DialogsPage />} />
          <Route path="dialogs/:id" element={<DialogDetailPage />} />
          <Route path="pipeline" element={<PipelineConfigPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="filter-stats" element={<FilterStatsPage />} />
          <Route path="prompts" element={<PromptsPage />} />
          <Route path="prompts/new" element={<PromptEditorPage />} />
          <Route path="prompts/:id" element={<PromptEditorPage />} />
          <Route path="guide" element={<GuidePage />} />
          <Route path="vacancies" element={<VacanciesPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
