// src/pages/RegistrationConfirmPage.tsx
import React, { useState, FormEvent, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import apiClient from '../services/api';
import { User, ApiError } from '../types';
import './FormStyles.css';

const RegistrationConfirmPage = () => {
  const [code, setCode] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const queryParams = new URLSearchParams(location.search);
    const emailFromQuery = queryParams.get('email');
    if (emailFromQuery) {
      setEmail(emailFromQuery);
    } else {
      setError("Email not provided for confirmation. Please restart registration.");
    }
  }, [location.search]);


  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email) {
        setError("Email is missing. Cannot confirm.");
        return;
    }
    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const response = await apiClient.post<User>('/auth/register/confirm', {
        email,
        code,
      });
      setSuccessMessage(`Registration successful for ${response.data.username}! You can now log in.`);
      // Опционально: автоматически перенаправить на логин через несколько секунд
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    } catch (err: any) {
      const apiError = err.response?.data as ApiError;
      if (apiError?.detail) {
        if (typeof apiError.detail === 'string') setError(apiError.detail);
        else setError(apiError.detail.map(d => d.msg).join(', '));
      } else {
        setError('Confirmation failed. Invalid or expired code.');
      }
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="form-container">
      <h2>Confirm Registration</h2>
      {error && <p className="error-message">{error}</p>}
      {successMessage && <p className="success-message">{successMessage}</p>}
      
      <form onSubmit={handleSubmit}>
        <p>A verification code was sent to <strong>{email || "your email"}</strong>. Please enter it below.</p>
        <div>
          <label htmlFor="email-confirm">Email (should be pre-filled)</label>
          <input 
            type="email" 
            id="email-confirm" 
            value={email} 
            onChange={(e) => setEmail(e.target.value)} // Позволяем менять, если вдруг не передался
            required 
            readOnly={!!location.search.includes('email=')} // Делаем readOnly, если email из query
          />
        </div>
        <div>
          <label htmlFor="code">Verification Code</label>
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
        <button type="submit" disabled={isLoading || !email || successMessage !== null}>
          {isLoading ? 'Confirming...' : 'Confirm Registration'}
        </button>
      </form>
      {successMessage && (
         <p><Link to="/login">Go to Login</Link></p>
      )}
      {!successMessage && (
        <p>Didn't receive a code? <Link to="/register">Try registering again</Link></p>
      )}
    </div>
  );
};

export default RegistrationConfirmPage;