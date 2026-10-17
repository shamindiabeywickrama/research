import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import CrowdPredictions from './pages/CrowdPredictions'
import StudyPlanner from './pages/StudyPlanner'
import Weather from './pages/Weather'
import ModelEvaluation from './pages/ModelEvaluation'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/predictions" element={<CrowdPredictions />} />
        <Route path="/study-planner" element={<StudyPlanner />} />
        <Route path="/weather" element={<Weather />} />
        <Route path="/model-evaluation" element={<ModelEvaluation />} />

        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
