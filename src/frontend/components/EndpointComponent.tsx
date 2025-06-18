import React, { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';

import { ActionButton } from './ActionButton';
import DeleteConfirmation from './DeleteConfirmation';
import { PyodideEndpoint, pyodideEngine } from './index';
import { InteractiveForm } from './InteractiveForm';
import { ApiResponse, EndpointComponentProps, FormData } from './types';
import { extractPathParams, formatResponse, getStatusColor } from './utils';

interface PyodideEndpointComponentProps extends EndpointComponentProps {
  endpoint: PyodideEndpoint;
}

// Component that executes Python endpoints
export const PyodideEndpointComponent: React.FC<
  PyodideEndpointComponentProps
> = ({ endpoint, onError }) => {
  const params = useParams();
  const [searchParams] = useSearchParams();
  const [data, setData] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const executeEndpoint = async (
    body?: FormData,
    customQueryParams?: Record<string, string | number | boolean | undefined>
  ) => {
    try {
      setLoading(true);
      setError(null);

      // Convert search params to object
      const queryParams: Record<string, string> = {};

      if (customQueryParams) {
        Object.entries(customQueryParams).forEach(([key, value]) => {
          if (value !== undefined && value !== null && value !== "") {
            queryParams[key] = String(value);
          }
        });
      } else {
        // Convert URLSearchParams to array first
        Array.from(searchParams.entries()).forEach(([key, value]) => {
          if (value !== undefined && value !== null && value !== "") {
            queryParams[key] = String(value);
          }
        });
      }

      // Convert params to plain object to avoid React Router type issues
      const pathParams: Record<string, string> = {};
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          pathParams[key] = value;
        }
      });

      // Fallback: Extract path parameters manually from URL if React Router fails
      if (
        Object.keys(pathParams).length === 0 ||
        Object.values(pathParams).some((v) => v.startsWith(":"))
      ) {
        const currentPath = window.location.pathname;
        const endpointPath = endpoint.path;
        const extractedParams = extractPathParams(currentPath, endpointPath);
        Object.assign(pathParams, extractedParams);

        console.log("🔍 Manual path parameter extraction:", {
          pathParams,
          currentPath,
          endpointPath,
        });
      }

      console.log("🚀 Executing with params:", {
        pathParams,
        queryParams,
        body,
      });
      console.log("🔗 Raw React Router params:", params);
      console.log("🌐 Current URL:", window.location.href);

      const result = await pyodideEngine.executeEndpoint(
        endpoint.operationId,
        pathParams,
        queryParams,
        body
      );

      setData(result);
    } catch (err) {
      const error = err as Error;
      setError(error);
      if (onError) {
        onError(error);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    console.log("🔌 PyodideEndpointComponent received endpoint:", endpoint);
    console.log("🔗 React Router params:", params);
    console.log(
      "🔍 Search params:",
      Object.fromEntries(searchParams.entries())
    );

    // Only auto-execute for GET requests
    if (endpoint.method === "GET") {
      executeEndpoint();
    } else {
      setLoading(false);
    }
  }, [endpoint.operationId, params, searchParams, onError]);

  const handleFormSubmit = async (formData: FormData) => {
    if (endpoint.operationId === "search_users") {
      // For search, use query parameters
      await executeEndpoint(undefined, formData);
    } else {
      // For POST/PUT, use request body
      await executeEndpoint(formData);
    }
  };

  const handleDelete = async () => {
    await executeEndpoint();
  };

  return (
    <div
      style={{
        padding: "20px",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}
    >
      <div style={{ marginBottom: "20px" }}>
        <Link
          to="/"
          style={{
            textDecoration: "none",
            color: "#2196f3",
            fontSize: "14px",
            fontWeight: "500",
          }}
        >
          ← Back to Home
        </Link>
      </div>
      <div
        style={{
          marginBottom: "20px",
          padding: "15px",
          backgroundColor: "#e3f2fd",
          borderRadius: "8px",
          borderLeft: "4px solid #2196f3",
        }}
      >
        <h2 style={{ margin: "0 0 10px 0", color: "#1976d2" }}>
          <span
            style={{
              backgroundColor:
                endpoint.method === "GET"
                  ? "#28a745"
                  : endpoint.method === "POST"
                  ? "#007bff"
                  : endpoint.method === "PUT"
                  ? "#ffc107"
                  : "#dc3545",
              color: endpoint.method === "PUT" ? "#212529" : "white",
              padding: "4px 8px",
              borderRadius: "4px",
              fontSize: "14px",
              fontWeight: "600",
              marginRight: "10px",
            }}
          >
            {endpoint.method}
          </span>
          {endpoint.path}
        </h2>
        {endpoint.summary && (
          <p
            style={{
              margin: "5px 0 0 0",
              color: "#1565c0",
              fontStyle: "italic",
            }}
          >
            {endpoint.summary}
          </p>
        )}
      </div>
      {/* Interactive Forms for POST/PUT/Search */}
      {(endpoint.method === "POST" ||
        endpoint.method === "PUT" ||
        endpoint.operationId === "search_users") &&
        ![
          "clear_persistence",
          "clear_backup_only",
          "reset_to_defaults",
          "save_to_persistence",
          "restore_from_persistence",
        ].includes(endpoint.operationId) && (
          <InteractiveForm endpoint={endpoint} onSubmit={handleFormSubmit} />
        )}
      {/* Action Buttons for Persistence Operations */}
      {[
        "clear_persistence",
        "clear_backup_only",
        "reset_to_defaults",
        "save_to_persistence",
        "restore_from_persistence",
      ].includes(endpoint.operationId) && (
        <ActionButton
          endpoint={endpoint}
          onAction={() => handleFormSubmit({})}
        />
      )}
      {/* Delete Confirmation */}
      {
        (endpoint.method === "DELETE" && (
          <DeleteConfirmation
            endpoint={endpoint}
            onConfirm={handleDelete}
            userId={params.user_id as string | undefined}
          />
        )) as React.ReactNode
      }
      {/* Loading State */}
      {loading && (
        <div
          style={{
            padding: "20px",
            textAlign: "center",
            backgroundColor: "#f8f9fa",
            borderRadius: "8px",
            border: "1px solid #dee2e6",
          }}
        >
          <div style={{ fontSize: "18px", marginBottom: "10px" }}>⏳</div>
          <div>Loading...</div>
        </div>
      )}
      {/* Error State */}
      {error && (
        <div
          style={{
            padding: "20px",
            backgroundColor: "#f8d7da",
            borderRadius: "8px",
            border: "1px solid #f5c6cb",
            color: "#721c24",
          }}
        >
          <h4 style={{ margin: "0 0 10px 0" }}>❌ Error</h4>
          <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>
            {error.message}
          </pre>
        </div>
      )}
      {/* Response Data */}
      {!loading && !error && data && (
        <div
          style={{
            backgroundColor: "#f8f9fa",
            borderRadius: "8px",
            border: "1px solid #dee2e6",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "15px",
              backgroundColor: "#e9ecef",
              borderBottom: "1px solid #dee2e6",
              display: "flex",
              alignItems: "center",
              gap: "10px",
            }}
          >
            <h4 style={{ margin: 0 }}>📋 Response</h4>
            {data && typeof data === "object" && "status_code" in data && (
              <span
                style={{
                  backgroundColor: getStatusColor(
                    (data as ApiResponse).status_code || 200
                  ),
                  color: "white",
                  padding: "4px 8px",
                  borderRadius: "4px",
                  fontSize: "12px",
                  fontWeight: "600",
                }}
              >
                {(data as ApiResponse).status_code || 200}
              </span>
            )}
          </div>
          <pre
            style={{
              margin: 0,
              padding: "20px",
              backgroundColor: "#ffffff",
              overflow: "auto",
              fontSize: "13px",
              lineHeight: "1.4",
            }}
          >
            {JSON.stringify(formatResponse(data), null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

// Re-export SmartEndpoint for convenience
export { SmartEndpoint } from "./SmartEndpoint";
