import { useCallback, useEffect, useMemo, useState } from "react";
import {
  useMutation,
  UseMutationOptions,
  useQuery,
  useQueryClient,
  UseQueryOptions,
} from "react-query";

import { getAPIClient } from "./client";
import { APIQueryOptions, PaginatedResponse, User } from "./types";

// Generic API hook
export const useAPI = (): ReturnType<typeof getAPIClient> => {
  const client = getAPIClient();
  return client;
};

// Query hook for GET requests
export const useAPIQuery = <T>(
  key: string | string[],
  url: string,
  options?: UseQueryOptions<T>
) => {
  const client = getAPIClient();

  return useQuery<T>(key, () => client.get<T>(url), options);
};

// Paginated query hook
export const usePaginatedQuery = <T>(
  baseKey: string,
  baseUrl: string,
  queryOptions?: APIQueryOptions,
  options?: UseQueryOptions<PaginatedResponse<T>>
) => {
  const client = getAPIClient();

  const buildUrl = (url: string, opts?: APIQueryOptions) => {
    if (!opts) return url;

    const params = new URLSearchParams();
    if (opts.page !== undefined) params.append("page", opts.page.toString());
    if (opts.pageSize !== undefined)
      params.append("page_size", opts.pageSize.toString());
    if (opts.sort) params.append("sort", opts.sort);
    if (opts.order) params.append("order", opts.order);
    if (opts.search) params.append("search", opts.search);

    if (opts.filters) {
      Object.entries(opts.filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, value.toString());
        }
      });
    }

    const queryString = params.toString();
    return queryString ? `${url}?${queryString}` : url;
  };

  return useQuery<PaginatedResponse<T>>(
    [baseKey, queryOptions],
    () => client.get<PaginatedResponse<T>>(buildUrl(baseUrl, queryOptions)),
    options
  );
};

// Mutation hook for POST/PUT/DELETE requests
export const useAPIMutation = <T, V = unknown>(
  url: string,
  method: "post" | "put" | "delete" | "patch" = "post",
  options?: UseMutationOptions<T, Error, V>
) => {
  const client = getAPIClient();

  return useMutation<T, Error, V>((data: V) => {
    switch (method) {
      case "post":
        return client.post<T>(url, data);
      case "put":
        return client.put<T>(url, data);
      case "delete":
        return client.delete<T>(url);
      case "patch":
        return client.patch<T>(url, data);
      default:
        throw new Error(`Unsupported method: ${method}`);
    }
  }, options);
};

// File upload hook
export const useFileUpload = <T = unknown>(
  url: string,
  options?: UseMutationOptions<
    T,
    Error,
    { file: File; onProgress?: (progress: number) => void }
  >
) => {
  const client = getAPIClient();

  return useMutation<
    T,
    Error,
    { file: File; onProgress?: (progress: number) => void }
  >(({ file, onProgress }) => client.upload<T>(url, file, onProgress), options);
};

// Invalidate queries hook
export const useInvalidateQueries = () => {
  const queryClient = useQueryClient();

  return {
    invalidateAll: () => queryClient.invalidateQueries(),
    invalidateByKey: (key: string | string[]) =>
      queryClient.invalidateQueries(key),
    removeByKey: (key: string | string[]) => queryClient.removeQueries(key),
    resetByKey: (key: string | string[]) => queryClient.resetQueries(key),
  };
};

// Optimistic updates hook
export const useOptimisticUpdate = <T>(
  queryKey: string | string[],
  updateFn: (oldData: T | undefined, newData: Partial<T>) => T
) => {
  const queryClient = useQueryClient();

  return {
    optimisticUpdate: (newData: Partial<T>) => {
      queryClient.setQueryData<T>(queryKey, (old) => updateFn(old, newData));
    },
    rollback: () => {
      queryClient.invalidateQueries(queryKey);
    },
  };
};

// Auto-generated hooks from OpenAPI schema
export const useUsers = (queryOptions?: APIQueryOptions) =>
  usePaginatedQuery<User>("users", "/users", queryOptions);

export const useUser = (id: string) =>
  useAPIQuery<User>(["user", id], `/users/${id}`, {
    enabled: !!id,
  });

export const useCreateUser = () =>
  useAPIMutation<User, Omit<User, "id" | "createdAt" | "updatedAt">>(
    "/users",
    "post"
  );

export const useUpdateUser = (id: string) =>
  useAPIMutation<User, Partial<Omit<User, "id" | "createdAt" | "updatedAt">>>(
    `/users/${id}`,
    "put"
  );

export const useDeleteUser = () =>
  useAPIMutation<void, string>("/users", "delete");

// Authentication hooks
export const useLogin = () =>
  useAPIMutation<
    { access_token: string; refresh_token: string; user: User },
    { email: string; password: string }
  >("/auth/login", "post");

export const useLogout = () =>
  useAPIMutation<void, void>("/auth/logout", "post");

export const useRefreshToken = () =>
  useAPIMutation<{ access_token: string }, { refresh_token: string }>(
    "/auth/refresh",
    "post"
  );

export const useCurrentUser = () =>
  useAPIQuery<User>("currentUser", "/auth/me");

// Authentication state management hook
export const useAuth = () => {
  const login = useLogin();
  const logout = useLogout();
  const refreshToken = useRefreshToken();
  const currentUser = useCurrentUser();
  // Track token changes with state
  const [tokenState, setTokenState] = useState(() =>
    localStorage.getItem("access_token")
  );

  // Listen for token changes in localStorage
  useEffect(() => {
    const handleStorageChange = () => {
      setTokenState(localStorage.getItem("access_token"));
    };

    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, []);

  const isAuthenticated = useMemo(() => {
    return !!tokenState;
  }, [tokenState]);
  const handleLogin = useCallback(
    async (credentials: { email: string; password: string }) => {
      try {
        const response = await login.mutateAsync(credentials);
        localStorage.setItem("access_token", response.access_token);
        localStorage.setItem("refresh_token", response.refresh_token);
        setTokenState(response.access_token); // Update state immediately
        return response;
      } catch (error) {
        throw error;
      }
    },
    [login]
  );
  const handleLogout = useCallback(async () => {
    try {
      await logout.mutateAsync();
    } finally {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      setTokenState(null); // Update state immediately
    }
  }, [logout]);

  return {
    isAuthenticated,
    user: currentUser.data,
    login: handleLogin,
    logout: handleLogout,
    refreshToken: refreshToken.mutateAsync,
    isLoading: login.isLoading || logout.isLoading || currentUser.isLoading,
    error: login.error || logout.error || currentUser.error,
  };
};

// Real-time hooks (WebSocket integration)
export const useWebSocket = (url: string) => {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [lastMessage, setLastMessage] = useState<MessageEvent | null>(null);
  const [readyState, setReadyState] = useState<number>(WebSocket.CONNECTING);

  useEffect(() => {
    const ws = new WebSocket(url);

    ws.onopen = () => setReadyState(WebSocket.OPEN);
    ws.onclose = () => setReadyState(WebSocket.CLOSED);
    ws.onerror = () => setReadyState(WebSocket.CLOSED);
    ws.onmessage = (event) => setLastMessage(event);

    setSocket(ws);

    return () => {
      ws.close();
    };
  }, [url]);

  const sendMessage = useCallback(
    (message: string) => {
      if (socket && readyState === WebSocket.OPEN) {
        socket.send(message);
      }
    },
    [socket, readyState]
  );

  return {
    socket,
    lastMessage,
    readyState,
    sendMessage,
  };
};
