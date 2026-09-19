import { useEffect } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';

import MainLayout from './components/MainLayout';
import { useAuthStore } from './stores/authStore';
import BoardPage from './pages/BoardPage';
import LoginPage from './pages/LoginPage';
import ReportPage from './pages/ReportPage';
import DirectoryPage from './pages/DirectoryPage';
import SettingsPage from './pages/SettingsPage';

export default function App() {
  const user = useAuthStore((s) => s.user);
  const initialized = useAuthStore((s) => s.initialized);
  const restore = useAuthStore((s) => s.restore);

  useEffect(() => {
    void restore();
  }, [restore]);

  if (!initialized) {
    return null;
  }

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
      {user ? (
        <Route element={<MainLayout />}>
          <Route path="/" element={<BoardPage />} />
          <Route path="/reports" element={<ReportPage />} />
          <Route path="/directories" element={<DirectoryPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      ) : (
        <Route path="*" element={<Navigate to="/login" replace />} />
      )}
    </Routes>
  );
}
