export interface Product {
  name: string;
  price: number;
  original_price?: number | null;
  // New field names
  image?: string | null;
  url?: string | null;
  store: 'dia' | 'coto';
  on_sale: boolean;
  discount_percent?: number | null;
  // Aliases for HTML template compatibility
  image_url?: string | null;
  product_url?: string | null;
  is_on_sale?: boolean;
  supermarket?: 'dia' | 'coto';
}

export interface BackendComparison {
  name: string;
  dia?: any;
  coto?: any;
  cheaper: 'dia' | 'coto' | 'equal' | null;
  savings?: number | null;
  savings_pct?: number | null;
}

export interface SearchResult {
  query: string;
  dia: Product[];
  coto: Product[];
  comparisons: BackendComparison[];
  total_dia: number;
  total_coto: number;
}

export interface ComparedProduct {
  dia?: Product;
  coto?: Product;
  cheapest: 'dia' | 'coto' | 'equal' | 'unknown';
  priceDiff?: number;
  priceDiffPercent?: number;
}
