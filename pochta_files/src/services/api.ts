// src/services/api.ts
import axios, { AxiosError } from 'axios';
import { AuthResponse, ApiError } from '../types';

const API_BASE_URL = '/api/v1'; // Адрес вашего бэкенда

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Интерцептор для добавления токена в заголовки
apiClient.interceptors.request.use(
  (config) => {
    const accessToken = localStorage.getItem('accessToken');
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Интерцептор для обработки ошибок и обновления токена
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error: AxiosError<ApiError>) => {
    const originalRequest = error.config;

    if (error.response) {
      const { status, data } = error.response;
      const detail = typeof data?.detail === 'string' ? data.detail : JSON.stringify(data?.detail);

      if (status === 401 && originalRequest && !originalRequest.url?.endsWith('/auth/refresh-token')) {
        const refreshToken = localStorage.getItem('refreshToken');
        if (refreshToken) {
          try {
            console.log('Attempting to refresh token...');
            // Убедимся, что apiClient.post не используется здесь, чтобы избежать бесконечного цикла интерцепторов
            const refreshResponse = await axios.post<AuthResponse>(`${API_BASE_URL}/auth/refresh-token`, {
              refresh_token: refreshToken,
            });
            
            const { access_token: newAccessToken, refresh_token: newRefreshToken } = refreshResponse.data;
            localStorage.setItem('accessToken', newAccessToken);
            localStorage.setItem('refreshToken', newRefreshToken);
            
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
            }
            return apiClient(originalRequest); // Повторяем оригинальный запрос с новым токеном
          } catch (refreshError: any) {
            console.error('Failed to refresh token:', refreshError.response?.data || refreshError.message);
            localStorage.removeItem('accessToken');
            localStorage.removeItem('refreshToken');
            // Сигнализируем приложению о необходимости разлогина (например, через AuthContext или событие)
            // window.location.href = '/login'; // Избегаем прямого window.location, если есть AuthContext
            // Вместо этого можно бросить специфическую ошибку или вернуть Promise.reject
            // чтобы AuthContext мог ее поймать и обработать.
             document.dispatchEvent(new CustomEvent('auth-error-logout')); // Событие для App.tsx/AuthContext
            return Promise.reject(refreshError); 
          }
        } else {
          console.log('No refresh token available, redirecting to login.');
          localStorage.removeItem('accessToken');
          document.dispatchEvent(new CustomEvent('auth-error-logout'));
        }
      } else if (status === 403) {
        console.warn('Access Denied (403):', detail);
        // Здесь можно показать пользователю сообщение "Доступ запрещен"
        // или перенаправить на специальную страницу.
        // Пока просто логируем и позволяем ошибке проброситься дальше.
        // Можно обернуть ошибку, чтобы компонент мог ее специфично обработать.
        // error.message = `Access Denied: ${detail || 'You do not have permission to access this resource.'}`;
      }
    } else if (error.request) {
      console.error('Network error or no response received:', error.message);
      // Ошибка сети, сервер не ответил
    } else {
      console.error('Error setting up request:', error.message);
    }
    return Promise.reject(error);
  }
);

export default apiClient;