// src/pages/FilesPage.tsx
import React, { useState, useEffect, ChangeEvent, FormEvent, useCallback } from 'react';
import apiClient from '../services/api';
import { FileInfo, FileListResponse, ApiError } from '../types';
import './FilesPage.css'; // Убедись, что этот файл стилей существует и подключен

const ITEMS_PER_PAGE_OPTIONS = [10, 25, 50, 100];
const DEFAULT_ITEMS_PER_PAGE = ITEMS_PER_PAGE_OPTIONS[0];

interface Filters {
  search: string;
  mime_type: string;
  date_from: string; // YYYY-MM-DD
  date_to: string;   // YYYY-MM-DD
}

type SortByFields = 'original_filename' | 'uploaded_at' | 'mime_type' | 'file_size_bytes' | '';

interface Sort {
  sort_by: SortByFields;
  sort_order: 'asc' | 'desc';
}

const FilesPage = () => {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  
  const [isLoading, setIsLoading] = useState(true); // Начинаем с загрузки
  const [uploading, setUploading] = useState(false);
  
  const [error, setError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Состояния для пагинации, фильтрации, поиска, сортировки
  const [currentPage, setCurrentPage] = useState(1);
  const [totalFiles, setTotalFiles] = useState(0);
  const [itemsPerPage, setItemsPerPage] = useState(DEFAULT_ITEMS_PER_PAGE);
  
  const [filters, setFilters] = useState<Filters>({
    search: '',
    mime_type: '',
    date_from: '',
    date_to: '',
  });
  // Используем отдельное состояние для фильтров, которые фактически отправляются в API
  // Это позволяет пользователю вводить данные без немедленной отправки запроса
  const [appliedFilters, setAppliedFilters] = useState<Partial<Filters>>({});

  const [sort, setSort] = useState<Sort>({
    sort_by: 'uploaded_at', // Сортировка по умолчанию
    sort_order: 'desc',
  });

  const totalPages = totalFiles > 0 ? Math.ceil(totalFiles / itemsPerPage) : 1;

  const fetchFiles = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.append('skip', ((currentPage - 1) * itemsPerPage).toString());
      params.append('limit', itemsPerPage.toString());

      // Добавляем примененные фильтры
      if (appliedFilters.search) params.append('search', appliedFilters.search);
      if (appliedFilters.mime_type) params.append('mime_type', appliedFilters.mime_type);
      if (appliedFilters.date_from) params.append('date_from', appliedFilters.date_from);
      if (appliedFilters.date_to) params.append('date_to', appliedFilters.date_to);
      
      // Добавляем сортировку
      if (sort.sort_by) params.append('sort_by', sort.sort_by);
      params.append('sort_order', sort.sort_order);
      
      const response = await apiClient.get<FileListResponse>(`/files?${params.toString()}`);
      setFiles(response.data.files);
      setTotalFiles(response.data.total_files);
    } catch (err: any) {
      const apiError = err.response?.data as ApiError;
      setError(apiError?.detail ? (typeof apiError.detail === 'string' ? apiError.detail : JSON.stringify(apiError.detail)) : 'Failed to fetch files.');
      console.error("Fetch files error:", err);
      setFiles([]); 
      setTotalFiles(0);
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, itemsPerPage, appliedFilters, sort]); // fetchFiles будет пересоздана при изменении этих зависимостей

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]); // Вызываем fetchFiles при монтировании и при изменении самой функции fetchFiles

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setSelectedFile(event.target.files[0]);
      setUploadError(null);
    } else {
      setSelectedFile(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadError('Please select a file to upload.');
      return;
    }
    setUploading(true);
    setUploadError(null);
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      await apiClient.post('/files/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      alert('File uploaded successfully!');
      setSelectedFile(null); 
      const fileInput = document.getElementById('file-upload-input') as HTMLInputElement;
      if (fileInput) fileInput.value = ""; // Очищаем input type="file"

      // Если после загрузки мы хотим видеть новый файл в списке,
      // и он должен появиться на первой странице по умолчанию (или по текущей сортировке)
      if (currentPage !== 1) {
        setCurrentPage(1); // Это вызовет fetchFiles через useEffect
      } else {
        fetchFiles(); // Если уже на первой, просто обновляем
      }
    } catch (err: any) {
      const apiError = err.response?.data as ApiError;
      setUploadError(apiError?.detail ? (typeof apiError.detail === 'string' ? apiError.detail : JSON.stringify(apiError.detail)) : 'File upload failed.');
      console.error("Upload error:", err);
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = async (fileId: number, filename: string) => {
    try {
        const response = await apiClient.get(`/files/${fileId}/download`, {
            responseType: 'blob', 
        });
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', filename); 
        document.body.appendChild(link);
        link.click();
        link.parentNode?.removeChild(link);
        window.URL.revokeObjectURL(url);
    } catch (err) {
        console.error('Download failed:', err);
        alert('Failed to download file.');
    }
  };
  
  const handleDelete = async (fileId: number) => {
    if (window.confirm("Are you sure you want to delete this file?")) {
        try {
            await apiClient.delete(`/files/${fileId}`);
            alert("File deleted successfully.");
            // Если удалили файл на последней странице, и она стала пустой,
            // возможно, стоит перейти на предыдущую страницу.
            if (files.length === 1 && currentPage > 1) {
                setCurrentPage(currentPage - 1);
            } else {
                fetchFiles(); 
            }
        } catch (err) {
            console.error("Delete failed:", err);
            alert("Failed to delete file.");
        }
    }
  };

  const handleFilterInputChange = (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFilters(prev => ({ ...prev, [name]: value }));
  };

  const handleApplyFilters = (e?: FormEvent) => { // Сделал e опциональным
    if (e) e.preventDefault();
    setCurrentPage(1); 
    setAppliedFilters(filters); 
  };

  const handleResetFilters = () => {
    setFilters({ search: '', mime_type: '', date_from: '', date_to: '' });
    setAppliedFilters({}); // Это вызовет fetchFiles через useEffect, если appliedFilters были не пустыми
    if(currentPage !== 1) setCurrentPage(1); // Также вызовет fetchFiles, если страница была не первая
    else if (Object.keys(appliedFilters).length > 0) fetchFiles(); // Если были фильтры и мы на 1 стр, просто обновляем
  };

  const handleSortFieldChange = (e: ChangeEvent<HTMLSelectElement>) => {
    const newSortBy = e.target.value as SortByFields;
    setSort(prev => ({ ...prev, sort_by: newSortBy, sort_order: 'desc' })); // При смене поля, ставим desc по умолчанию
    setCurrentPage(1);
  };

  const toggleSortOrder = () => {
    setSort(prev => ({ ...prev, sort_order: prev.sort_order === 'asc' ? 'desc' : 'asc' }));
    setCurrentPage(1); // Сортировка обычно применяется с первой страницы
  };
  
  const handleItemsPerPageChange = (e: ChangeEvent<HTMLSelectElement>) => {
    setItemsPerPage(Number(e.target.value));
    setCurrentPage(1); 
  };

  return (
    <div className="files-page-container">
      <h2>My Files</h2>
      
      <div className="upload-section card">
        <h3>Upload New File (under 50 Mb)</h3>
        <input type="file" id="file-upload-input" onChange={handleFileChange} />
        <button onClick={handleUpload} disabled={!selectedFile || uploading}>
          {uploading ? 'Uploading...' : 'Upload'}
        </button>
        {uploadError && <p className="error-message upload-error">{uploadError}</p>}
      </div>

      <form onSubmit={handleApplyFilters} className="filters-section card">
        <h3>Filters & Search</h3>
        <div className="filter-grid">
          <input
            type="text"
            name="search"
            placeholder="Search by name/type..."
            value={filters.search}
            onChange={handleFilterInputChange}
          />
          <input
            type="text"
            name="mime_type"
            placeholder="MIME type (e.g. image, pdf)"
            value={filters.mime_type}
            onChange={handleFilterInputChange}
          />
          <label htmlFor="date_from_filter" className="date-label">From:</label>
          <input
            type="date"
            id="date_from_filter"
            name="date_from"
            value={filters.date_from}
            onChange={handleFilterInputChange}
          />
          <label htmlFor="date_to_filter" className="date-label">To:</label>
          <input
            type="date"
            id="date_to_filter"
            name="date_to"
            value={filters.date_to}
            onChange={handleFilterInputChange}
          />
        </div>
        <div className="filter-actions">
            <button type="submit">Apply Filters</button>
            <button type="button" onClick={handleResetFilters}>Reset Filters</button>
        </div>
      </form>

      <div className="controls-section card">
        <label htmlFor="sort-by">Sort by: </label>
        <select id="sort-by" value={sort.sort_by} onChange={handleSortFieldChange}>
          <option value="uploaded_at">Upload Date</option>
          <option value="original_filename">Filename</option>
          <option value="mime_type">MIME Type</option>
          <option value="file_size_bytes">File Size</option>
        </select>
        <button onClick={toggleSortOrder}>
          Order: {sort.sort_order === 'asc' ? 'Ascending ↑' : 'Descending ↓'}
        </button>
        <label htmlFor="items-per-page" style={{marginLeft: '20px'}}>Items per page: </label>
        <select id="items-per-page" value={itemsPerPage} onChange={handleItemsPerPageChange}>
            {ITEMS_PER_PAGE_OPTIONS.map(opt => <option key={opt} value={opt}>{opt}</option>)}
        </select>
      </div>

      {isLoading && <div className="card"><p>Loading files...</p></div>}
      {error && <div className="card"><p className="error-message">Error loading files: {error}</p></div>}
      
      {!isLoading && !error && (
        <>
          {files.length === 0 ? (
            <p className="card">You haven't uploaded any files yet, or no files match your current filters.</p>
          ) : (
            <ul className="file-list">
              {files.map((file) => (
                <li key={file.file_id} className="file-item card">
                  <div className="file-info">
                    <strong>{file.original_filename}</strong>
                    <small>Type: {file.mime_type}</small>
                    <small>Size: {(file.file_size_bytes / 1024).toFixed(2)} KB</small>
                    <small>Uploaded: {new Date(file.uploaded_at).toLocaleString()}</small>
                  </div>
                  <div className="file-actions">
                    <button onClick={() => handleDownload(file.file_id, file.original_filename)}>Download</button>
                    <button onClick={() => handleDelete(file.file_id)} className="delete-button">Delete</button>
                  </div>
                </li>
              ))}
            </ul>
          )}

          {totalPages > 1 && (
            <div className="pagination card">
              <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1}>
                Previous
              </button>
              <span> Page {currentPage} of {totalPages} (Total: {totalFiles}) </span>
              <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages}>
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default FilesPage;