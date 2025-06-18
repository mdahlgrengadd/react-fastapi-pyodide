import { ApiResponse } from './types';

export const getMethodColor = (method: string): string => {
  switch (method) {
    case "GET":
      return "#28a745";
    case "POST":
      return "#007bff";
    case "PUT":
      return "#ffc107";
    case "DELETE":
      return "#dc3545";
    case "PATCH":
      return "#6f42c1";
    default:
      return "#6c757d";
  }
};

export const getStatusColor = (statusCode: number): string => {
  if (statusCode >= 200 && statusCode < 300) return "#28a745";
  if (statusCode >= 400 && statusCode < 500) return "#dc3545";
  if (statusCode >= 500) return "#6f42c1";
  return "#17a2b8";
};

export const formatResponse = (data: unknown): unknown => {
  if (data && typeof data === "object" && "content" in data) {
    return {
      ...data,
      content: (data as ApiResponse).content,
    };
  }
  return data;
};

export const convertOpenAPIPathToReactRouter = (
  openAPIPath: string
): string => {
  return openAPIPath.replace(/{([^}]+)}/g, ":$1");
};

export const extractPathParams = (
  currentPath: string,
  endpointPath: string
): Record<string, string> => {
  const pathParams: Record<string, string> = {};

  // Extract parameters by matching the endpoint path pattern with current path
  const pathPattern = endpointPath.replace(/{([^}]+)}/g, "([^/]+)");
  const regex = new RegExp(`^${pathPattern}$`);
  const match = currentPath.match(regex);

  if (match) {
    // Extract parameter names from the endpoint path
    const paramNames = [...endpointPath.matchAll(/{([^}]+)}/g)].map(
      (m) => m[1]
    );

    // Map matched values to parameter names
    paramNames.forEach((paramName, index) => {
      if (match[index + 1]) {
        pathParams[paramName] = match[index + 1];
      }
    });
  }

  return pathParams;
};
