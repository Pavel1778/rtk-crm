import { useEffect } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { useIsFetching, useIsMutating } from '@tanstack/react-query';

import CookieConsentBanner from './components/CookieConsentBanner';
import MainLayout from './components/MainLayout';
import { useAuthStore } from './stores/authStore';
import BoardPage from './pages/BoardPage';
import LoginPage from './pages/LoginPage';
import ReportPage from './pages/ReportPage';
import DirectoryPage from './pages/DirectoryPage';
import SettingsPage from './pages/SettingsPage';
import AuditLogPage from './pages/AuditLogPage';
import HelpPage from './pages/HelpPage';
import CookiePolicyPage from './pages/CookiePolicyPage';
import PrivacyPolicyPage from './pages/PrivacyPolicyPage';

export default function App() {
  const isFetching = useIsFetching();
  const isMutating = useIsMutating();
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
    <>
    {(isFetching > 0 || isMutating > 0) && <div className="global-progress-bar" />}
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route path="/cookie-policy" element={<CookiePolicyPage />} />
      <Route path="/privacy" element={<PrivacyPolicyPage />} />
      {user ? (
        <Route element={<MainLayout />}>
          <Route path="/" element={<BoardPage />} />
          <Route path="/reports" element={<ReportPage />} />
          <Route path="/directories" element={<DirectoryPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/audit" element={<AuditLogPage />} />
          <Route path="/help" element={<HelpPage />} />
        </Route>
      ) : (
        <Route path="*" element={<Navigate to="/login" replace />} />
      )}
    </Routes>
    <CookieConsentBanner />
    </>
  );
}
