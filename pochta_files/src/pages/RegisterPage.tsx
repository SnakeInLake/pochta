// src/pages/RegisterPage.tsx
import React, { useState, FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import apiClient from '../services/api';
import { ApiError } from '../types';
import './FormStyles.css';

const RegisterPage = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      await apiClient.post('/auth/register/initiate', {
        username,
        email,
        password,
      });
      // Перенаправляем на страницу подтверждения, передавая email
      navigate(`/register/confirm?email=${encodeURIComponent(email)}`);
      alert('Registration initiated. Please check your email for a verification code.');
    } catch (err: any) {
      const apiError = err.response?.data as ApiError;
      if (apiError?.detail) {
        if (typeof apiError.detail === 'string') setError(apiError.detail);
        else setError(apiError.detail.map(d => d.msg).join(', '));
      } else {
        setError('Registration failed. Please try again.');
      }
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="form-container">
      <h2>Register</h2>
      {error && <p className="error-message">{error}</p>}
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="username">Username</label>
          <input type="text" id="username" value={username} onChange={(e) => setUsername(e.target.value)} required />
        </div>
        <div>
          <label htmlFor="email">Email</label>
          <input type="email" id="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div>
          <label htmlFor="password">Password</label>
          <input type="password" id="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8}/>
        </div>
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Registering...' : 'Register (Send Code)'}
        </button>
      </form>
      <p>
        Already have an account? <Link to="/login">Login here</Link>
      </p>
    </div>
  );
};

export default RegisterPage;