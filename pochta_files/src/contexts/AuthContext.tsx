// src/contexts/AuthContext.tsx
import React, { createContext, useState, useContext, useEffect, ReactNode } from 'react';
import { User } from '../types';
import apiClient from '../services/api'; // Если понадобится запрос /me

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  accessToken: string | null;
  login: (accessToken: string, refreshToken: string) => Promise<void>; // Добавил refreshToken
  logout: () => void;
  isLoading: boolean; // Для отображения загрузки при проверке токена
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [accessToken, setAccessToken] = useState<string | null>(localStorage.getItem('accessToken'));
  const [user, setUser] = useState<User | null>(null); // Пока не получаем /me, но можно добавить
  const [isLoading, setIsLoading] = useState(true);

  // Функция для получения данных пользователя (опционально)
  const fetchUser = async (token: string) => {
      if (token) { // Добавил проверку, что токен есть
        try {
            // apiClient уже будет использовать интерцептор с этим токеном
            // const response = await apiClient.get<User>('/users/me'); // Если есть такой эндпоинт
            // setUser(response.data);
            // В нашем случае, после логина мы можем просто считать пользователя аутентифицированным
            // без запроса /me, если он не нужен для отображения данных сразу.
            // Пока оставим user null, если нет эндпоинта /me
            setUser(null); // ЗАГЛУШКА
        } catch (error) {
            console.error('Failed to fetch user data:', error);
            logout(); // Если токен невалиден, разлогиниваем
        }
      } else {
        setUser(null);
      }
      setIsLoading(false);
  };
  
  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      setAccessToken(token);
      fetchUser(token); // Проверяем токен и получаем данные пользователя
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (newAccessToken: string, newRefreshToken: string) => {
    localStorage.setItem('accessToken', newAccessToken);
    localStorage.setItem('refreshToken', newRefreshToken);
    setAccessToken(newAccessToken);
    await fetchUser(newAccessToken); // Получаем данные пользователя после логина
  };

  const logout = () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    setAccessToken(null);
    setUser(null);
    // Можно добавить запрос на бэкенд /auth/logout для аннулирования refresh token
    // apiClient.post('/auth/logout', { refresh_token: localStorage.getItem('refreshToken')});
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated: !!accessToken, user, accessToken, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};