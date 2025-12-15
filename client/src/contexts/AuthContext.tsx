/**
 * Authentication Context for Phase 13 - User Authentication
 * 
 * Provides authenticated user state and helper functions throughout the app.
 * User authentication is handled server-side via Kerberos headers.
 * This context manages the client-side user state and permissions.
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import api from '@/lib/api';

export interface User {
  kerberos_id: string;
  display_name: string;
  email: string;
  groups: string[];
  roles: string[];
  is_active: boolean;
}

export interface Permission {
  VIEW: boolean;
  EDIT: boolean;
  DELETE: boolean;
  SHARE: boolean;
  ANALYZE: boolean;
  EXPORT: boolean;
  VIEW_AUDIT: boolean;
  MANAGE_USERS: boolean;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  error: string | null;
  hasRole: (role: string) => boolean;
  hasPermission: (permission: keyof Permission) => boolean;
  inGroup: (group: string) => boolean;
  refetchUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCurrentUser = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get('/auth/me');
      setUser(response.data);
    } catch (err: any) {
      console.error('Failed to fetch current user:', err);
      // Don't set error for 401 - user is just not authenticated
      if (err.response?.status !== 401) {
        setError(err.response?.data?.detail || 'Failed to load user information');
      }
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCurrentUser();
  }, []);

  const hasRole = (role: string): boolean => {
    if (!user) return false;
    return user.roles.includes(role.toUpperCase());
  };

  const hasPermission = (permission: keyof Permission): boolean => {
    if (!user) return false;
    
    // Admin has all permissions
    if (hasRole('ADMIN')) return true;
    
    // Role-to-permission mapping (matches backend logic)
    const rolePermissions: Record<string, Set<string>> = {
      VIEWER: new Set(['VIEW', 'ANALYZE', 'EXPORT']),
      CONTRIBUTOR: new Set(['VIEW', 'EDIT', 'SHARE', 'ANALYZE', 'EXPORT']),
      AUDITOR: new Set(['VIEW', 'VIEW_AUDIT']),
      ADMIN: new Set(['VIEW', 'EDIT', 'DELETE', 'SHARE', 'ANALYZE', 'EXPORT', 'VIEW_AUDIT', 'MANAGE_USERS']),
    };

    for (const role of user.roles) {
      const permissions = rolePermissions[role];
      if (permissions?.has(permission)) {
        return true;
      }
    }

    return false;
  };

  const inGroup = (group: string): boolean => {
    if (!user) return false;
    return user.groups.includes(group);
  };

  const refetchUser = async () => {
    await fetchCurrentUser();
  };

  const value: AuthContextType = {
    user,
    loading,
    error,
    hasRole,
    hasPermission,
    inGroup,
    refetchUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
