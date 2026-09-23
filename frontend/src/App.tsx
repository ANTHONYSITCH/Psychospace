import { Navigate, Route, Routes } from 'react-router-dom'
import { MainLayout } from './components/layout/MainLayout'
import { DashboardPage } from './pages/Dashboard'
import { QuestionnairePage } from './pages/Questionnaire'
import { HistoryPage } from './pages/History'
import { EnvironmentPage } from './pages/Environment'
import { AIAnalysisPage } from './pages/AIAnalysis'
import { ProfilePage } from './pages/Profile'

export default function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/dashboard" element={<Navigate to="/" replace />} />
        <Route path="/questionnaire" element={<QuestionnairePage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/environment" element={<EnvironmentPage />} />
        <Route path="/ai-analysis" element={<AIAnalysisPage />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Route>
    </Routes>
  )
}
