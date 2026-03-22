/**
 * API client for the Mini Outfit Builder backend.
 *
 * When NEXT_PUBLIC_API_URL is set, use it directly (e.g. http://localhost:8000 for local dev).
 * When it's not set (production behind nginx), API calls go to the same origin
 * so the nginx reverse proxy routes /api/* to the backend automatically.
 */

import axios from "axios";

function getApiBaseUrl(): string {
  // If explicitly configured, use that
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  // In the browser: use same origin (nginx proxy handles routing)
  if (typeof window !== "undefined") {
    return window.location.origin;
  }
  // Server-side rendering: talk to backend container directly
  return "http://backend:8000";
}

const API_BASE_URL = getApiBaseUrl();

const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

// ── Types ──

export interface Product {
  id: string;
  name: string;
  brand: string | null;
  price: number;
  color: string | null;
  description: string | null;
  image_url: string | null;
  product_url: string;
  category: "TOP" | "BOTTOM" | "SHOE" | "ACCESSORY";
  taxonomy: string | null;
  google_product_category: string | null;
  google_taxonomy_id: number | null;
  availability: boolean;
  source: "ZAPPOS" | "AMAZON" | "SSENSE" | "HNM";
  style_tags: string[];
  last_updated: string | null;
  created_at: string | null;
}

export interface Outfit {
  id: string;
  top: Product;
  bottom: Product;
  shoe: Product;
  accessory: Product;
  style_tags: string[];
  score: number;
  created_at: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// ── API Functions ──

export async function searchOutfits(
  query: string,
  page: number = 1,
  perPage: number = 12
): Promise<PaginatedResponse<Outfit>> {
  const { data } = await api.get<PaginatedResponse<Outfit>>(
    "/outfits/search",
    {
      params: { q: query, page, per_page: perPage },
    }
  );
  return data;
}

export async function getOutfits(
  page: number = 1,
  perPage: number = 12
): Promise<PaginatedResponse<Outfit>> {
  const { data } = await api.get<PaginatedResponse<Outfit>>("/outfits", {
    params: { page, per_page: perPage },
  });
  return data;
}

export async function getOutfitById(id: string): Promise<Outfit> {
  const { data } = await api.get<Outfit>(`/outfits/${id}`);
  return data;
}

export async function getProducts(params: {
  category?: string;
  source?: string;
  min_price?: number;
  max_price?: number;
  page?: number;
  per_page?: number;
}): Promise<PaginatedResponse<Product>> {
  const { data } = await api.get<PaginatedResponse<Product>>("/products", {
    params,
  });
  return data;
}

export async function searchProducts(
  query: string,
  page: number = 1,
  perPage: number = 20
): Promise<PaginatedResponse<Product>> {
  const { data } = await api.get<PaginatedResponse<Product>>(
    "/products/search",
    {
      params: { q: query, page, per_page: perPage },
    }
  );
  return data;
}

export async function getProductStats(): Promise<Record<string, number>> {
  const { data } = await api.get<Record<string, number>>("/products/stats");
  return data;
}

export default api;
