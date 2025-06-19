import "swagger-ui-react/swagger-ui.css";

import React, { Suspense, useEffect, useState } from "react";
import SwaggerUI from "swagger-ui-react"; // ← static import

import { pyodideEngine } from "./index";

// // Lazy load SwaggerUI to reduce initial bundle size, with error handling
// const SwaggerUI = lazy(async () => {
//   try {
//     return await import("swagger-ui-react");
//   } catch (error) {
//     console.warn("Failed to load SwaggerUI:", error);
//     // Return a fallback component
//     return {
//       default: () => (
//         <div style={{ padding: "20px", textAlign: "center" }}>
//           <h2>API Documentation</h2>
//           <p>
//             SwaggerUI failed to load. This might be due to a development mode
//             bundling issue.
//           </p>
//           <p>
//             Try running in preview mode instead:{" "}
//             <code>npm run preview:gh-pages</code>
//           </p>
//           <details style={{ marginTop: "20px", textAlign: "left" }}>
//             <summary>Error Details</summary>
//             <pre
//               style={{
//                 background: "#f5f5f5",
//                 padding: "10px",
//                 marginTop: "10px",
//               }}
//             >
//               {error?.toString() || "Unknown error loading SwaggerUI"}
//             </pre>
//           </details>
//         </div>
//       ),
//     };
//   }
// });

interface PyodideSwaggerUIProps {
  onError?: (error: Error) => void;
}

interface OpenAPISpec {
  openapi?: string;
  info?: {
    title: string;
    version: string;
    description?: string;
  };
  paths?: Record<string, Record<string, unknown>>;
  components?: Record<string, unknown>;
}

// Loading component for SwaggerUI
const SwaggerUILoading: React.FC = () => (
  <div className="flex items-center justify-center p-8">
    <div className="text-center">
      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto mb-2"></div>
      <p className="text-sm text-gray-600">Loading API Documentation...</p>
    </div>
  </div>
);

export const PyodideSwaggerUI: React.FC<PyodideSwaggerUIProps> = ({
  onError,
}) => {
  const [openApiSpec, setOpenApiSpec] = useState<OpenAPISpec | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadSchema = async () => {
      try {
        setLoading(true);

        // Wait a bit to ensure Pyodide is fully initialized
        await new Promise((resolve) => setTimeout(resolve, 100));

        const schema = pyodideEngine.getOpenAPISchema();
        if (!schema) {
          throw new Error("No OpenAPI schema available");
        }

        console.log(" OpenAPI Schema loaded:", schema);
        setOpenApiSpec(schema as OpenAPISpec);
      } catch (error) {
        console.error("Failed to load OpenAPI schema:", error);
        onError?.(error as Error);
      } finally {
        setLoading(false);
      }
    };

    loadSchema();
  }, [onError]);

  // Modify the OpenAPI spec to use a base URL we can intercept
  const modifiedSpec = React.useMemo(() => {
    if (!openApiSpec) return null;

    return {
      ...openApiSpec,
      servers: [
        {
          url: "/api/backend",
          description: "Pyodide FastAPI Server",
        },
      ],
    };
  }, [openApiSpec]);

  // Set up a global fetch interceptor for swagger requests
  React.useEffect(() => {
    const originalFetch = window.fetch;

    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url =
        typeof input === "string"
          ? input
          : input instanceof URL
          ? input.toString()
          : input.url;

      // Intercept requests to our Pyodide API
      if (url.includes("/api/backend/")) {
        console.log(" Intercepted Swagger UI request:", url, init);

        try {
          // Extract the actual API path
          const urlObj = new URL(url, window.location.origin);
          const pathname = urlObj.pathname.replace("/api/backend", "");
          const method = (init?.method || "GET").toUpperCase();

          console.log(` Processing Pyodide request: ${method} ${pathname}`);

          // Find the matching endpoint
          const endpoints = pyodideEngine.getEndpoints();
          const endpoint = endpoints.find((ep) => {
            // Match the path pattern
            const pathPattern = ep.path.replace(/{([^}]+)}/g, "([^/]+)");
            const regex = new RegExp(`^${pathPattern}$`);
            return regex.test(pathname) && ep.method === method;
          });

          if (!endpoint) {
            console.error(` Endpoint not found: ${method} ${pathname}`);
            throw new Error(`Endpoint not found: ${method} ${pathname}`);
          }

          console.log(` Found endpoint: ${endpoint.operationId}`);

          // Extract path parameters
          const pathParams: Record<string, string> = {};
          const pathPattern = endpoint.path.replace(/{([^}]+)}/g, "([^/]+)");
          const regex = new RegExp(`^${pathPattern}$`);
          const match = pathname.match(regex);

          if (match) {
            const paramNames = [...endpoint.path.matchAll(/{([^}]+)}/g)].map(
              (m) => m[1]
            );
            paramNames.forEach((paramName, index) => {
              if (match[index + 1]) {
                pathParams[paramName] = match[index + 1];
              }
            });
          }

          // Extract query parameters
          const queryParams: Record<string, unknown> = {};
          urlObj.searchParams.forEach((value, key) => {
            queryParams[key] = value;
          }); // Parse request body
          let body = null;
          if (init?.body) {
            try {
              if (typeof init.body === "string") {
                // Fix common Python/JavaScript boolean differences in the JSON
                let bodyStr = init.body;
                bodyStr = bodyStr.replace(/:\s*True\b/g, ": true");
                bodyStr = bodyStr.replace(/:\s*False\b/g, ": false");
                bodyStr = bodyStr.replace(/:\s*None\b/g, ": null");

                body = JSON.parse(bodyStr);
                console.log(" Parsed body:", body);
              } else {
                body = init.body;
              }
            } catch (error) {
              console.error(
                " Failed to parse request body:",
                error,
                "Original body:",
                init.body
              );
              body = init.body;
            }
          }

          console.log(` Executing endpoint with:`, {
            operationId: endpoint.operationId,
            pathParams,
            queryParams,
            body,
          });

          // Execute through Pyodide
          const result = await pyodideEngine.executeEndpoint(
            endpoint.operationId,
            pathParams,
            queryParams,
            body
          );

          console.log(" Pyodide execution result:", result);
          const content = (result as { content?: unknown }).content || result;
          const statusCode =
            (result as { status_code?: number }).status_code || 200;
          const responseText = JSON.stringify(content, null, 2);

          // Create a proper Response object
          const response = new Response(responseText, {
            status: statusCode,
            statusText: statusCode < 300 ? "OK" : "Error",
            headers: {
              "Content-Type": "application/json",
              "Access-Control-Allow-Origin": "*",
              "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
              "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
          });

          return response;
        } catch (error) {
          console.error(" Pyodide execution error:", error);
          const errorMessage = JSON.stringify(
            {
              detail: (error as Error).message,
              error: "Internal Server Error",
            },
            null,
            2
          );

          return new Response(errorMessage, {
            status: 500,
            statusText: "Internal Server Error",
            headers: {
              "Content-Type": "application/json",
              "Access-Control-Allow-Origin": "*",
            },
          });
        }
      }

      // For all other requests, use the original fetch
      return originalFetch(input, init);
    };

    // Cleanup function to restore original fetch
    return () => {
      window.fetch = originalFetch;
    };
  }, []);

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
          backgroundColor: "#fafafa",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: "24px", marginBottom: "10px" }}>
            Loading API Documentation...
          </div>
          <div style={{ color: "#666" }}>
            Preparing Swagger UI for Pyodide FastAPI
          </div>
        </div>
      </div>
    );
  }

  if (!modifiedSpec) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
          backgroundColor: "#fafafa",
        }}
      >
        <div style={{ textAlign: "center", color: "#666" }}>
          <div style={{ fontSize: "24px", marginBottom: "10px" }}>
            No API Documentation Available
          </div>
          <div>
            The OpenAPI schema could not be loaded from the Pyodide instance.
          </div>
        </div>
      </div>
    );
  }
  return (
    <div style={{ height: "100vh", overflow: "auto" }}>
      <Suspense fallback={<SwaggerUILoading />}>
        <SwaggerUI
          spec={modifiedSpec}
          docExpansion="list"
          defaultModelsExpandDepth={1}
          tryItOutEnabled={true}
        />
      </Suspense>
    </div>
  );
};
