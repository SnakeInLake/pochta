// src/types.ts
export interface User {
  user_id: number;
  username: string;
  email: string;
  created_at: string; 
  updated_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface FileInfo {
  file_id: number;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  stored_filename_uuid: string; // UUID обычно строка
  uploaded_at: string;
}

export interface FileListResponse {
  files: FileInfo[];
  total_files: number;
}

export interface ApiErrorDetail {
  type: string;
  loc: (string | number)[];
  msg: string;
  input: any;
  url?: string;
}

export interface ApiError {
  detail: string | ApiErrorDetail[]; // Ошибка может быть строкой или списком деталей
}