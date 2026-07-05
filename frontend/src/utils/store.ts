import { create } from 'zustand';

interface AuthState {
  token: string | null;
  user: any | null;
  isAuthenticated: boolean;
  setToken: (token: string) => void;
  setUser: (user: any) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('token'),
  user: null,
  isAuthenticated: !!localStorage.getItem('token'),
  
  setToken: (token: string) => {
    localStorage.setItem('token', token);
    set({ token, isAuthenticated: true });
  },
  
  setUser: (user: any) => {
    set({ user });
  },
  
  logout: () => {
    localStorage.removeItem('token');
    set({ token: null, user: null, isAuthenticated: false });
  },
}));

interface UiState {
  sidebarOpen: boolean;
  currentOrgId: string | null;
  currentProjectId: string | null;
  setSidebarOpen: (open: boolean) => void;
  setCurrentOrg: (orgId: string) => void;
  setCurrentProject: (projectId: string) => void;
}

export const useUiStore = create<UiState>((set) => ({
  sidebarOpen: true,
  currentOrgId: null,
  currentProjectId: null,
  
  setSidebarOpen: (open: boolean) => {
    set({ sidebarOpen: open });
  },
  
  setCurrentOrg: (orgId: string) => {
    set({ currentOrgId: orgId });
  },
  
  setCurrentProject: (projectId: string) => {
    set({ currentProjectId: projectId });
  },
}));
