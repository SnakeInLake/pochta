// src/App.tsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Navbar from './components/Navbar';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import RegistrationConfirmPage from './pages/RegistrationConfirmPage';
import FilesPage from './pages/FilesPage';
import NotFoundPage from './pages/NotFoundPage';
import './styles/global.css'; // Подключим глобальные стили

// Защищенный роут
const ProtectedRoute = () => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <div>Loading authentication status...</div>; // Или спиннер
  }

  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />;
};

function AppContent() {
  const { isLoading } = useAuth(); // Получаем isLoading, чтобы не рендерить ничего до проверки
  if (isLoading) {
      return <div>Checking authentication...</div>;
  }
  return (
    <>
      <Navbar />
      <main className="container">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/register/confirm" element={<RegistrationConfirmPage />} />
          
          {/* Защищенные роуты */}
          <Route element={<ProtectedRoute />}>
            <Route path="/files" element={<FilesPage />} />
            <Route path="/" element={<Navigate to="/files" replace />} /> {/* Главная редиректит на файлы */}
          </Route>
          
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </Router>
  );
}

export default App;