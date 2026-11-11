import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { Dashboard } from "./pages/Dashboard";
import { Trades } from "./pages/Trades";
import { Risk } from "./pages/Risk";
import { Accounts } from "./pages/Accounts";
import { Research } from "./pages/Research";

export function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<Dashboard />} />
          <Route path="trades" element={<Trades />} />
          <Route path="risk" element={<Risk />} />
          <Route path="accounts" element={<Accounts />} />
          <Route path="research" element={<Research />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
