import axios from 'axios';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export const api = axios.create({ baseURL: `${BACKEND_URL}/api` });

export function setAuthToken(token) {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common['Authorization'];
  }
}

const stored = localStorage.getItem('sdg_token');
if (stored) setAuthToken(stored);

// ---- OKR tasks (weekly execution) ----
export const tasksApi = {
  generateWeek: (weekStart) => api.post('/org/tasks/generate-week', { week_start: weekStart }),
  list: (params) => api.get('/org/tasks', { params }),
  mine: () => api.get('/org/tasks/mine'),
  update: (id, body) => api.patch(`/org/tasks/${id}`, body),
  review: (id) => api.post(`/org/tasks/${id}/ai-review`),
  detectStage: (id) => api.post(`/org/tasks/${id}/stage`),
  weeklyDigest: () => api.get('/org/tasks/weekly-digest'),
  departmentHeads: () => api.get('/org/department-heads'),
  setDepartmentHead: (body) => api.put('/org/department-heads', body),
};

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const detail = error.response?.data?.detail || '';
    if (status === 402) {
      window.dispatchEvent(new CustomEvent('sdg-insufficient-credits', {
        detail: detail.includes('token limit') ? 'Monthly token limit reached. Top up or wait for your next billing cycle.' : detail || 'Not enough credits.',
      }));
    } else if (!error.response || (status >= 500 && status < 600)) {
      const msg = detail
        || (status >= 500 ? 'The server had a problem. Please try again.' : 'Could not reach the server. Check your connection.');
      toast.error(msg);
    }
    return Promise.reject(error);
  }
);
