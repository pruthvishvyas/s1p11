import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { TerminologyProvider } from './contexts/TerminologyContext';
import { OutcomeProvider } from './contexts/OutcomeContext';
import Dashboard from './pages/Dashboard';
import { TABS } from './utils/tabs';

export default function App() {
  const first = TABS[0];
  return (
    <BrowserRouter>
      <TerminologyProvider>
        <OutcomeProvider>
          <Routes>
            <Route path="/:outcome/:tab" element={<Dashboard />} />
            <Route path="*" element={<Navigate to={'/' + first.outcome + '/' + first.key} replace />} />
          </Routes>
        </OutcomeProvider>
      </TerminologyProvider>
    </BrowserRouter>
  );
}
