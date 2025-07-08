import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '';

// API client configuration
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// User Management
export const userAPI = {
  createUser: async (userData) => {
    const response = await apiClient.post('/users', userData);
    return response.data;
  }
};

// KYC API endpoints
export const kycAPI = {
  // Submit KYC request
  submitKYC: async (kycData) => {
    const response = await apiClient.post('/kyc/submit', kycData);
    return response.data;
  },

  // Check KYC status
  getStatus: async (ticketId) => {
    const response = await apiClient.get(`/kyc/status/${ticketId}`);
    return response.data;
  },

  // Get user's KYC status
  getUserStatus: async (userId) => {
    const response = await apiClient.get(`/kyc/user/${userId}/status`);
    return response.data;
  },

  // Delete user data (GDPR)
  deleteUserData: async (userId) => {
    const response = await apiClient.delete(`/kyc/user/${userId}/data`);
    return response.data;
  }
};

// Admin API endpoints
export const adminAPI = {
  // Get pending KYC reviews
  getPendingReviews: async () => {
    const response = await apiClient.get('/admin/pending');
    return response.data;
  },

  // Submit admin review
  submitReview: async (ticketId, reviewData) => {
    const response = await apiClient.post(`/admin/review/${ticketId}`, reviewData);
    return response.data;
  },

  // Get KYC statistics
  getStats: async () => {
    const response = await apiClient.get('/admin/stats');
    return response.data;
  }
};

// File upload utility
export const fileAPI = {
  // Upload file via backend proxy (recommended approach)
  uploadFile: async (file, fileType) => {
    try {
      // Map frontend file types to backend expected types
      const fileTypeMapping = {
        'doc_front': 'id_front',
        'doc_back': 'id_back',
        'selfie': 'selfie'
      };
      
      const backendFileType = fileTypeMapping[fileType] || fileType;
      
      // Validate file type
      const allowedTypes = ['id_front', 'id_back', 'selfie'];
      if (!allowedTypes.includes(backendFileType)) {
        throw new Error(`Invalid file type: ${fileType}. Expected: doc_front, doc_back, or selfie`);
      }

      console.log(`Starting upload for ${fileType} (${backendFileType}) via backend proxy...`);

      // Create FormData for file upload
      const formData = new FormData();
      formData.append('file', file);
      formData.append('file_type', backendFileType);

      // Upload file via backend proxy
      const response = await apiClient.post('/files/file', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 60000, // 60 seconds for file upload
      });
      
      const { file_url, object_name, file_size } = response.data;
      
      console.log(`Upload successful for ${fileType}:`, file_url);

      return {
        url: file_url,
        object_name: object_name,
        file_size: file_size
      };
      
    } catch (error) {
      console.error(`File upload error for ${fileType}:`, error);
      
      // Enhanced error handling
      if (error.response) {
        // Backend returned an error response
        const status = error.response.status;
        const message = error.response.data?.detail || error.response.data?.message || 'Unknown error';
        
        if (status === 400) {
          throw new Error(`Invalid file: ${message}`);
        } else if (status === 413) {
          throw new Error(`File too large: ${message}`);
        } else if (status === 422) {
          throw new Error(`Validation error: ${message}`);
        } else {
          throw new Error(`Upload failed (${status}): ${message}`);
        }
      } else if (error.request) {
        // Network error
        throw new Error(`Network error: Cannot reach upload server`);
      } else {
        // Other error
        throw new Error(`Failed to upload ${fileType}: ${error.message}`);
      }
    }
  },

  // Legacy presigned URL upload (kept for backward compatibility)
  uploadFilePresigned: async (file, fileType) => {
    try {
      // Map frontend file types to backend expected types
      const fileTypeMapping = {
        'doc_front': 'id_front',
        'doc_back': 'id_back',
        'selfie': 'selfie'
      };
      
      const backendFileType = fileTypeMapping[fileType] || fileType;
      
      // Validate file type
      const allowedTypes = ['id_front', 'id_back', 'selfie'];
      if (!allowedTypes.includes(backendFileType)) {
        throw new Error(`Invalid file type: ${fileType}. Expected: doc_front, doc_back, or selfie`);
      }

      console.log(`Starting upload for ${fileType} (${backendFileType})...`);

      // Step 1: Get presigned upload URL from backend
      const presignedResponse = await apiClient.post('/upload/presigned-url', {
        file_type: backendFileType,
        content_type: file.type || 'image/jpeg'
      });
      
      const { upload_url, file_url, object_name } = presignedResponse.data;
      
      console.log(`Got presigned URL for ${fileType}:`, upload_url.substring(0, 100) + '...');

      // Step 2: Upload file directly to MinIO using presigned URL
      const uploadResponse = await fetch(upload_url, {
        method: 'PUT',
        body: file,
        headers: {
          'Content-Type': file.type || 'image/jpeg',
        },
      });
      
      if (!uploadResponse.ok) {
        throw new Error(`Upload failed: ${uploadResponse.statusText} (${uploadResponse.status})`);
      }
      
      console.log(`Upload successful for ${fileType}:`, file_url);

      // Step 3: Return the final file URL
      return {
        url: file_url,
        object_name: object_name
      };
      
    } catch (error) {
      console.error(`File upload error for ${fileType}:`, error);
      
      // Enhanced error handling for network issues
      if (error.message.includes('Failed to fetch') || 
          error.message.includes('ERR_NAME_NOT_RESOLVED') ||
          error.message.includes('Network Error')) {
        console.warn('Network error detected - MinIO may not be accessible from browser');
        
        // Provide fallback mock URLs for development
        const mockUrls = {
          'doc_front': 'http://localhost:9000/kyc-documents/mock_id_front.jpg',
          'doc_back': 'http://localhost:9000/kyc-documents/mock_id_back.jpg',
          'selfie': 'http://localhost:9000/kyc-documents/mock_selfie.jpg'
        };
        
        // Simulate upload delay
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        return { url: mockUrls[fileType] || mockUrls.selfie };
      }
      
      throw new Error(`Failed to upload ${fileType}: ${error.message}`);
    }
  },

  // Convert file to base64 for preview
  fileToBase64: (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result);
      reader.onerror = error => reject(error);
    });
  }
};

// Utility functions
export const utils = {
  // Generate UUID v4
  generateUUID: () => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      var r = (Math.random() * 16) | 0, v = c === 'x' ? r : ((r & 0x3) | 0x8);
      return v.toString(16);
    });
  },

  // Format timestamp
  formatTimestamp: (timestamp) => {
    return new Date(timestamp).toLocaleString();
  },

  // Get status color
  getStatusColor: (status) => {
    const colors = {
      'pending': '#ff9800',
      'processing': '#2196f3',
      'approved': '#4caf50',
      'rejected': '#f44336',
      'manual_review': '#9c27b0'
    };
    return colors[status] || '#666';
  },

  // Get status icon
  getStatusIcon: (status) => {
    const icons = {
      'pending': '⏳',
      'processing': '🔄',
      'approved': '✅',
      'rejected': '❌',
      'manual_review': '👥'
    };
    return icons[status] || '❓';
  }
};

const api = {
  userAPI,
  kycAPI,
  adminAPI,
  fileAPI,
  utils
};

export default api;
