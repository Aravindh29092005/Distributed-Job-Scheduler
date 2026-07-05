import React, { createContext, useContext } from 'react';
import { useAuthStore } from '../utils/store';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const store = useAuthStore();
  return (
    <AuthContext.Provider value={{ user: store.user, isAuthenticated: store.isAuthenticated, login: store.login, logout: store.logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext() {
  return useContext(AuthContext);
}
