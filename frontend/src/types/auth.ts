export interface AuthResponse {
  access_token: string;
  user: {
    id: string;
    email: string;
    full_name: string | null;
  };
}
