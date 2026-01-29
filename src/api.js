import axios from 'axios';

const API = axios.create({
    baseURL: process.env.REACT_APP_API_URL || 'http://localhost:5000',
});

export const fetchBills = () => API.get('/api/dashboard');
export const fetchStats = () => API.get('/api/stats');
export const triggerSync = () => API.post('/api/sync', { 
    folder_id: process.env.REACT_APP_DRIVE_FOLDER_ID 
});
export const clearAllData = () => API.delete('/api/clear');

export default API;