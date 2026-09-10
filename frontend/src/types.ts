export interface BookData {
  id: number;
  title: string;
  date_published: string;
  blurb: string;
  length: number;
  cover_url: string;
  link: string;
  average_rating: number;
  num_ratings: number;
  num_reviews: number;
}

export interface UserData {
  id: number;
  netid: string;
  bio: string;
  reputation: number;
  followers: number;
  following: number;
}

export interface ReviewData {
  id: number;
  rating: number;
  review: string;
  user_id: number;
  user_netid: string;
  updated_at: string;
  book: Pick<BookData, 'id' | 'title' | 'cover_url'>;
}

export interface AuthorData { id: number; name: string }
export interface GenreData { id: number; genre: string }
