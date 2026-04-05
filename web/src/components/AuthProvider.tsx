"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import {
  signIn as cognitoSignIn,
  signOut as cognitoSignOut,
  getSession,
  getIdToken,
} from "@/lib/auth";

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  userEmail: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
  getToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  isLoading: true,
  userEmail: null,
  signIn: async () => {},
  signOut: () => {},
  getToken: async () => null,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [userEmail, setUserEmail] = useState<string | null>(null);

  useEffect(() => {
    getSession().then((session) => {
      if (session) {
        setIsAuthenticated(true);
        const payload = session.getIdToken().decodePayload();
        setUserEmail(payload.email || null);
      }
      setIsLoading(false);
    });
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const session = await cognitoSignIn(email, password);
    setIsAuthenticated(true);
    const payload = session.getIdToken().decodePayload();
    setUserEmail(payload.email || null);
  }, []);

  const signOut = useCallback(() => {
    cognitoSignOut();
    setIsAuthenticated(false);
    setUserEmail(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ isAuthenticated, isLoading, userEmail, signIn, signOut, getToken: getIdToken }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
