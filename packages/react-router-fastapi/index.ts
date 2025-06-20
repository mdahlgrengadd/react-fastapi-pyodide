// Main entry point
export { FastAPIRouter } from "./router/FastAPIRouter";
export { RouteGuard } from "./router/RouteGuard";
export { useFastAPIRouter } from "./router/hooks";
export {
  useAPI,
  useAPIQuery,
  useAPIMutation,
  usePaginatedQuery,
  useFileUpload,
} from "./api/hooks";
export { createAPIClient } from "./api/client";
export { updateAPIClientBaseURL } from "./api/client";
export { isAPIClientInitialized } from "./api/client";
export { generateTypes } from "./utils/generator";
export { generateRoutesFromSchema } from "./utils/schema";

// Types
export type {
  FastAPIRouterProps,
  RouteConfig,
  APIEndpoint,
  AuthConfig,
} from "./router/types";

export type {
  APIClientConfig,
  APIResponse,
  APIError,
  TokenResponse,
  User,
  PaginatedResponse,
  APIQueryOptions,
} from "./api/types";
