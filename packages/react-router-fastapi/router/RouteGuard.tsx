import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { AuthConfig } from './types';

interface RouteGuardProps {
  children: React.ReactNode;
  requiresAuth?: boolean;
  roles?: string[];
  authConfig?: AuthConfig;
  loadingComponent?: React.ComponentType;
  errorComponent?: React.ComponentType<{ error: Error }>;
}

export const RouteGuard: React.FC<RouteGuardProps> = ({
  children,
  requiresAuth = false,
  roles = [],
  authConfig,
  loadingComponent: LoadingComponent = DefaultLoading,
  errorComponent: ErrorComponent = DefaultError
}) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [user, setUser] = useState<any>(null);
  const [error, setError] = useState<Error | null>(null);
  const location = useLocation();

  useEffect(() => {
    const checkAuthentication = async () => {
      if (!requiresAuth && roles.length === 0) {
        setIsAuthenticated(true);
        return;
      }

      try {
        if (authConfig?.checkAuth) {
          const authenticated = await authConfig.checkAuth();
          setIsAuthenticated(authenticated);

          if (authenticated && authConfig.getUser) {
            const userData = await authConfig.getUser();
            setUser(userData);
          }
        } else {
          // Default token-based auth check
          const token = localStorage.getItem(authConfig?.tokenKey || 'token');
          setIsAuthenticated(!!token);
        }
      } catch (err) {
        setError(err as Error);
        setIsAuthenticated(false);
      }
    };

    checkAuthentication();
  }, [requiresAuth, roles, authConfig]);

  if (error) {
    return <ErrorComponent error={error} />;
  }

  if (isAuthenticated === null) {
    return <LoadingComponent />;
  }

  if (requiresAuth && !isAuthenticated) {
    return (
      <Navigate
        to={authConfig?.loginPath || '/login'}
        state={{ from: location }}
        replace
      />
    );
  }

  if (roles.length > 0 && user) {
    const userRoles = user.roles || [];
    const hasRequiredRole = roles.some(role => userRoles.includes(role));
    
    if (!hasRequiredRole) {
      return <div>Access denied. Insufficient permissions.</div>;
    }
  }

  return <>{children}</>;
};

const DefaultLoading: React.FC = () => (
  <div className="flex justify-center items-center p-8">
    <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
  </div>
);

const DefaultError: React.FC<{ error: Error }> = ({ error }) => (
  <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
    <strong className="font-bold">Error: </strong>
    <span className="block sm:inline">{error.message}</span>
  </div>
);