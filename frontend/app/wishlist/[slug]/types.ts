export type Reservation = {
  id: number;
  user_id?: number | null;
  user_name?: string | null;
  user_email?: string | null;
};

export type Contribution = {
  id: number;
  user_id: number;
  amount: number;
  user_name?: string | null;
  user_email?: string | null;
};

export type Gift = {
  id: number;
  title: string;
  url?: string | null;
  price?: number | null;
  image_url?: string | null;
  is_collective: boolean;
  is_private: boolean;
  is_reserved: boolean;
  reservation: Reservation | null;
  contributions: Contribution[];
  total_contributions: number;
  collected_percent: number;
  is_fully_collected: boolean;
};

export type Wishlist = {
  id: number;
  slug: string;
  title: string;
  description?: string | null;
  event_date?: string | null;
  privacy?: "link_only" | "friends" | "public";
  owner_id: number;
  gifts: Gift[];
  public_token?: string | null;
};

export type OgPreviewResponse = {
  url: string;
  title?: string | null;
  price?: number | null;
  image_url?: string | null;
  description?: string | null;
  brand?: string | null;
  currency?: string | null;
  availability?: string | null;
};

// Re-export from auth store for convenience
export type { User } from "../../../store/auth";
