import { useState } from "react";

import { ChatPage } from "./pages/ChatPage";
import { LoginPage } from "./pages/LoginPage";
import { AuthResponse } from "./types/auth";
import { User } from "./types/index";

export function App() {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);

  function handleAuthenticated(authData: AuthResponse) {
    setUser(authData.user);
    setToken(authData.access_token);
    localStorage.setItem("token", authData.access_token);
  }

  function handleLogout() {
    setUser(null);
    setToken(null);
    localStorage.removeItem("token");
  }

  if (!user || !token) {
    return <LoginPage onAuthenticated={handleAuthenticated} />;
  }

  return <ChatPage user={user} token={token} onLogout={handleLogout} />;
}
