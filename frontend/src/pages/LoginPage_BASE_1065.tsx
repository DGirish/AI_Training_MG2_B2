import { FormEvent, useEffect, useRef, useState } from "react";

import { getGoogleClientId, signIn, signInWithGoogle, signUp } from "../lib/api";
import { AuthResponse } from "../types/auth";


const ALLOWED_SIGNUP_DOMAINS = new Set(["amzur.com", "stackyon.com"]);


function hasAllowedSignupDomain(email: string): boolean {
  const parts = email.trim().toLowerCase().split("@");
  if (parts.length !== 2) {
    return false;
  }
  return ALLOWED_SIGNUP_DOMAINS.has(parts[1]);
}

interface LoginPageProps {
  onAuthenticated: (authData: AuthResponse) => void;
}

export function LoginPage({ onAuthenticated }: Readonly<LoginPageProps>) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [isSignUp, setIsSignUp] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [googleClientId, setGoogleClientId] = useState<string | null>(null);
  const googleButtonRef = useRef<HTMLDivElement | null>(null);
  let submitLabel = "Sign In";
  if (isLoading) {
    submitLabel = "Loading...";
  } else if (isSignUp) {
    submitLabel = "Sign Up";
  }

  useEffect(() => {
    if (isSignUp) {
      return;
    }

    let isMounted = true;
    getGoogleClientId()
      .then((clientId) => {
        if (isMounted) {
          setGoogleClientId(clientId);
        }
      })
      .catch(() => {
        if (isMounted) {
          setGoogleClientId(null);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [isSignUp]);

  useEffect(() => {
    if (isSignUp || !googleClientId || !googleButtonRef.current) {
      return;
    }

    const initializeGoogleButton = () => {
      if (!globalThis.google?.accounts?.id || !googleButtonRef.current) {
        return;
      }

      globalThis.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: async (response: { credential?: string }) => {
          if (!response.credential) {
            setError("Google authentication failed. Missing token.");
            return;
          }

          setError(null);
          setSuccessMessage(null);
          setIsLoading(true);
          try {
            const authData = await signInWithGoogle(response.credential);
            onAuthenticated(authData);
          } catch (err) {
            setError(err instanceof Error ? err.message : "Google authentication failed");
          } finally {
            setIsLoading(false);
          }
        },
      });

      googleButtonRef.current.innerHTML = "";
      globalThis.google.accounts.id.renderButton(googleButtonRef.current, {
        theme: "outline",
        size: "large",
        text: "continue_with",
        shape: "pill",
      });
    };

    const existingScript = document.getElementById("google-identity-services");
    if (existingScript) {
      initializeGoogleButton();
      return;
    }

    const script = document.createElement("script");
    script.id = "google-identity-services";
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = initializeGoogleButton;
    document.head.appendChild(script);
  }, [googleClientId, isSignUp, onAuthenticated]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccessMessage(null);

    if (isSignUp && !hasAllowedSignupDomain(email)) {
      setError("Use your amzur.com or stackyon.com email address to sign up.");
      return;
    }

    setIsLoading(true);

    try {
      if (isSignUp) {
        await signUp(email, password, fullName);
        setIsSignUp(false);
        setPassword("");
        setFullName("");
        setSuccessMessage("Account created successfully. Sign in to continue.");
        return;
      }

      const result = await signIn(email, password);
      onAuthenticated(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="auth-container">
      <section className="auth-card">
        <h1>{isSignUp ? "Create Account" : "Sign In"}</h1>

        <form onSubmit={handleSubmit} className="auth-form">
          {isSignUp && (
            <input
              type="text"
              placeholder="Full Name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          )}

          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          {isSignUp && (
            <p className="auth-hint">Use your amzur.com or stackyon.com email address.</p>
          )}

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
          />

          <button type="submit" disabled={isLoading}>
            {submitLabel}
          </button>
        </form>

        {!isSignUp && (
          <>
            <div className="auth-divider">
              <span>or</span>
            </div>
            <div className="auth-google" ref={googleButtonRef} />
          </>
        )}

        {error && <p className="auth-error">{error}</p>}
        {successMessage && <p className="auth-success">{successMessage}</p>}

        <p className="auth-toggle">
          {isSignUp ? "Already have an account?" : "Need an account?"}{" "}
          <button
            type="button"
            onClick={() => {
              setIsSignUp(!isSignUp);
              setError(null);
              setSuccessMessage(null);
            }}
            className="auth-link"
          >
            {isSignUp ? "Sign In" : "Sign Up"}
          </button>
        </p>
      </section>
    </main>
  );
}
