import axios from "axios";

import { clearToken, getToken } from "./auth";

const baseURL = process.env.NEXT_PUBLIC_API_BASE ?? "/api/v1";

export const api = axios.create({
  baseURL,
  timeout: 30_000,
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      clearToken();
    }
    return Promise.reject(err);
  },
);
