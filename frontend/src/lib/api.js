import axios from 'axios';

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
