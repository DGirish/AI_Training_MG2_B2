export interface User {
  id: string;
  email: string;
  full_name: string | null;
}

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
}

export interface ChatThread {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages?: ChatMessage[];
}

export interface AuthResponse {
  access_token: string;
  user: User;
}

