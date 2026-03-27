/** GET /api/books sort=… */
export type LibraryListSort = "default" | "title" | "rating" | "added";

export interface Book {
  id: string;
  title: string;
  author: string;
  rating: number | null;
  review: string;
  tags: string[];
  notes_md: string;
  source_path: string;
  position: number;
  created_at: string;
  updated_at: string;
}

export interface BooksResponse {
  books: Book[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface SyncResult {
  created: number;
  updated: number;
  total: number;
}

export interface WeightedTag {
  name: string;
  weight: number;
}

export interface ReaderProfile {
  top_genres: WeightedTag[];
  top_themes: WeightedTag[];
  preferred_moods: string[];
  preferred_complexity: string;
  favorite_authors: string[];
  summary: string;
  books_analyzed: number;
}

export interface Recommendation {
  title: string;
  author: string;
  genres: string[];
  themes?: string[];
  reasoning: string;
  match_score: number;
}

export interface RecommendationsResponse {
  library_size: number;
  recommendations: Recommendation[];
  from_cache: boolean;
}

export interface ReadingListEntry {
  id: string;
  title: string;
  author: string;
  genres: string[];
  reasoning: string;
  created_at: string;
}

export interface ReadingListsResponse {
  planned: ReadingListEntry[];
  blacklist: ReadingListEntry[];
}

export interface ReadingListToggleResult {
  planned: boolean;
  blacklist: boolean;
}

export interface EnrichResponse {
  enriched_count: number;
  books: unknown[];
}

export interface AppSettings {
  api_key: string;
  base_url: string;
  model_profile: string;
  model_recommend: string;
}

export interface TestConnectionResult {
  status: string;
}

export interface SettingsStatus {
  has_api_key: boolean;
  demo_library: boolean;
}
