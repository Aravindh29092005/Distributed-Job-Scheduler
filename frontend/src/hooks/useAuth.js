import { useAuthStore } from '../utils/store';
export function useAuth() {
  const store = useAuthStore();
  return {
    user: store.user,
    isAuthenticated: store.isAuthenticated,
    login: store.login,
    logout: store.logout,
  };
}
export default useAuth;
