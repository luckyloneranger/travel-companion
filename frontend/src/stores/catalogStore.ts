import { create } from "zustand";
import { listCities, getCity, getVariantDetail, type CityResponse, type CityDetailResponse, type VariantDetailResponse } from "@/lib/api";

interface CatalogStore {
  cities: CityResponse[];
  totalCities: number;
  selectedCity: CityDetailResponse | null;
  selectedVariant: VariantDetailResponse | null;
  loading: boolean;
  error: string | null;
  fetchCities: (params?: { region?: string; sort?: string; limit?: number; offset?: number }) => Promise<void>;
  fetchCity: (cityId: string) => Promise<void>;
  fetchVariant: (cityId: string, variantId: string) => Promise<void>;
  clearSelection: () => void;
}

export const useCatalogStore = create<CatalogStore>((set) => ({
  cities: [],
  totalCities: 0,
  selectedCity: null,
  selectedVariant: null,
  loading: false,
  error: null,

  fetchCities: async (params) => {
    set({ loading: true, error: null });
    try {
      const data = await listCities(params);
      set({ cities: data.cities, totalCities: data.total, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  fetchCity: async (cityId) => {
    set({ loading: true, error: null });
    try {
      const city = await getCity(cityId);
      set({ selectedCity: city, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  fetchVariant: async (cityId, variantId) => {
    set({ loading: true, error: null });
    try {
      const variant = await getVariantDetail(cityId, variantId);
      set({ selectedVariant: variant, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  clearSelection: () => set({ selectedCity: null, selectedVariant: null }),
}));
