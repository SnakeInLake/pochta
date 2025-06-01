// src/pages/LoginPage.tsx
import React, { useState, FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import apiClient from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { AuthResponse, ApiError, ApiErrorDetail } from '../types';
import './FormStyles.css'; // Общие стили для форм

const LoginPage = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [emailFor2FA, setEmailFor2FA] = useState(''); // Сохраняем email для шага 2FA
  const [code, setCode] = useState('');
  const [step, setStep] = useState(1); // 1: username/password, 2: 2FA code
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleLoginSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      // Шаг 1: Запрос кода 2FA
      // Бэкенд должен найти email по username
      const userFor2FAResponse = await apiClient.post('/auth/login/request-2fa-code', { username, password });
      // Предполагаем, что бэкенд вернет email пользователя или username, если email не нужен явно
      // или мы можем просто использовать email, который пользователь введет для 2FA (если бэкенд его найдет)
      // Для простоты, будем использовать username, а бэкенд найдет email.
      // Либо, если пользователь должен ввести email для 2FA, то нужно поле для email.
      // Давайте предположим, что пользователь вводит свой email на шаге 2FA
      setStep(2);
      alert('2FA code sent. Please check your email.');

    } catch (err: any) {
      const apiError = err.response?.data as ApiError;
      if (apiError?.detail) {
        if (typeof apiError.detail === 'string') setError(apiError.detail);
        else setError(apiError.detail.map(d => d.msg).join(', '));
      } else {
        setError('Login failed. Please try again.');
      }
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handle2FASubmit = async (e: FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    if (!emailFor2FA) {
        setError("Email for 2FA verification is missing. Please restart login.");
        setIsLoading(false);
        setStep(1);
        return;
    }
    try {
      // Шаг 2: Верификация кода 2FA
      const response = await apiClient.post<AuthResponse>('/auth/login/verify-2fa', {
        email: emailFor2FA, // Используем email, который пользователь ввел для 2FA
        code,
      });
      await login(response.data.access_token, response.data.refresh_token);
      navigate('/files');
    } catch (err: any) {
      const apiError = err.response?.data as ApiError;
       if (apiError?.detail) {
        if (typeof apiError.detail === 'string') setError(apiError.detail);
        else setError(apiError.detail.map(d => d.msg).join(', '));
      } else {
        setError('2FA verification failed.');
      }
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="form-container">
      <h2>Login</h2>
      {error && <p className="error-message">{error}</p>}
      {step === 1 && (
        <form onSubmit={handleLoginSubmit}>
          <div>
            <label htmlFor="username">Username</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          <div>
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button type="submit" disabled={isLoading}>
            {isLoading ? 'Requesting Code...' : 'Request 2FA Code'}
          </button>
        </form>
      )}
      {step === 2 && (
        <form onSubmit={handle2FASubmit}>
          <p>A 2FA code has been sent to your email associated with username: {username}. Please also enter your email.</p>
          <div>
            <label htmlFor="emailFor2FA">Your Email</label>
            <input
              type="email"
              id="emailFor2FA"
              value={emailFor2FA}
              onChange={(e) => setEmailFor2FA(e.target.value)}
              required
              placeholder="Enter email for 2FA code"
            />
          </div>
          <div>
            <label htmlFor="code">2FA Code</label>
            <input
              type="text"
              id="code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              required
              minLength={6}
              maxLength={6}
            />
          </div>
          <button type="submit" disabled={isLoading}>
            {isLoading ? 'Verifying...' : 'Login'}
          </button>
          <button type="button" onClick={() => setStep(1)} disabled={isLoading} className="link-button">
            Back to username/password
          </button>
        </form>
      )}
       <p>
        Don't have an account? <Link to="/register">Register here</Link>
      </p>
    </div>
  );
};

export default LoginPage;