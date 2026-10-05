import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { TerminologyProvider } from './contexts/TerminologyContext';
import { OutcomeProvider } from './contexts/OutcomeContext';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import { TABS } from './utils/tabs';

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="center-note">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  const first = TABS[0];
  return (
    <BrowserRouter>
      <AuthProvider>
        <TerminologyProvider>
          <OutcomeProvider>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/:outcome/:tab" element={<Protected><Dashboard /></Protected>} />
              <Route path="*" element={<Navigate to={'/' + first.outcome + '/' + first.key} replace />} />
            </Routes>
          </OutcomeProvider>
        </TerminologyProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
