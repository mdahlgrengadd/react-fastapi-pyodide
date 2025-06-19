import React, { useCallback, useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { PyodideEndpoint, pyodideEngine } from "./index";
import { EndpointComponentProps, FormData } from "./types";
import { extractPathParams, getStatusColor } from "./utils";

interface StreamingEndpointComponentProps extends EndpointComponentProps {
  endpoint: PyodideEndpoint;
  updateInterval?: number;
  maxUpdates?: number;
}

interface StreamUpdate {
  id: string;
  timestamp: string;
  data: Record<string, unknown>;
  step?: number;
  isComplete: boolean;
}

interface ResultData {
  status_code?: number;
  content?: {
    monitoring_session?: {
      live_data?: Array<Record<string, unknown>>;
    };
    simulation?: {
      results?: Array<Record<string, unknown>>;
    };
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

// Streaming component for real-time async endpoint updates
export const StreamingEndpointComponent: React.FC<
  StreamingEndpointComponentProps
> = ({ endpoint, onError, maxUpdates = 20 }) => {
  const params = useParams();
  const [searchParams] = useSearchParams();
  const [updates, setUpdates] = useState<StreamUpdate[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [finalResult, setFinalResult] = useState<ResultData | null>(null);

  // Check if this endpoint supports streaming
  const isStreamingEndpoint =
    endpoint.operationId.includes("async") ||
    endpoint.operationId.includes("monitor") ||
    endpoint.operationId.includes("stream");

  const executeEndpoint = useCallback(
    async (
      body?: FormData,
      customQueryParams?: Record<string, string | number | boolean | undefined>
    ) => {
      // Convert params
      const queryParams: Record<string, string> = {};
      if (customQueryParams) {
        Object.entries(customQueryParams).forEach(([key, value]) => {
          if (value !== undefined && value !== null && value !== "") {
            queryParams[key] = String(value);
          }
        });
      } else {
        Array.from(searchParams.entries()).forEach(([key, value]) => {
          if (value !== undefined && value !== null && value !== "") {
            queryParams[key] = String(value);
          }
        });
      }

      const pathParams: Record<string, string> = {};
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          pathParams[key] = value;
        }
      });

      if (Object.keys(pathParams).length === 0) {
        const currentPath = window.location.pathname;
        const endpointPath = endpoint.path;
        const extractedParams = extractPathParams(currentPath, endpointPath);
        Object.assign(pathParams, extractedParams);
      }

      return (await pyodideEngine.executeEndpoint(
        endpoint.operationId,
        pathParams,
        queryParams,
        body
      )) as ResultData;
    },
    [endpoint, params, searchParams]
  );

  const addUpdate = useCallback(
    (
      updateData: Record<string, unknown>,
      step?: number,
      isComplete = false
    ) => {
      const newUpdate: StreamUpdate = {
        id: `update-${Date.now()}-${Math.random()}`,
        timestamp: new Date().toISOString(),
        data: updateData,
        step,
        isComplete,
      };

      setUpdates((prev) => {
        const updated = [...prev, newUpdate];
        return updated.slice(-maxUpdates);
      });
    },
    [maxUpdates]
  );

  const handleMonitoringStream = useCallback(
    async (
      body?: FormData,
      customQueryParams?: Record<string, string | number | boolean | undefined>
    ) => {
      const duration = Number(customQueryParams?.monitor_duration || 5);
      addUpdate({
        status: "monitoring",
        message: `Starting monitoring for ${duration} iterations...`,
      });

      // Execute the full monitoring operation
      const result = await executeEndpoint(body, customQueryParams);
      const liveData =
        (result?.content?.monitoring_session?.live_data as Array<
          Record<string, unknown>
        >) || [];

      // Show each monitoring iteration progressively
      for (let i = 0; i < liveData.length; i++) {
        const iteration = liveData[i];
        addUpdate(
          {
            iteration: i + 1,
            ...iteration,
          },
          i + 1,
          i === liveData.length - 1
        );

        // Add delay for visual effect
        await new Promise((resolve) => setTimeout(resolve, 200));
      }

      setFinalResult(result);
    },
    [executeEndpoint, addUpdate]
  );

  const handleSimulationStream = useCallback(
    async (
      body?: FormData,
      customQueryParams?: Record<string, string | number | boolean | undefined>
    ) => {
      const steps = Number(customQueryParams?.steps || 5);
      addUpdate({
        status: "simulation",
        message: `Starting simulation with ${steps} steps...`,
      });

      const result = await executeEndpoint(body, customQueryParams);
      const simulationResults =
        (result?.content?.simulation?.results as Array<
          Record<string, unknown>
        >) || [];

      // Show each step progressively
      for (let i = 0; i < simulationResults.length; i++) {
        const step = simulationResults[i];
        addUpdate(step, i + 1, i === simulationResults.length - 1);

        // Add delay for visual effect
        await new Promise((resolve) => setTimeout(resolve, 300));
      }

      setFinalResult(result);
    },
    [executeEndpoint, addUpdate]
  );

  const startStreaming = useCallback(
    async (
      body?: FormData,
      customQueryParams?: Record<string, string | number | boolean | undefined>
    ) => {
      try {
        setIsStreaming(true);
        setError(null);
        setUpdates([]);
        setFinalResult(null);

        if (!isStreamingEndpoint) {
          // For non-streaming endpoints, just execute normally
          addUpdate({ status: "executing", message: "Executing operation..." });
          const result = await executeEndpoint(body, customQueryParams);
          addUpdate(
            { status: "completed", message: "Operation completed" },
            undefined,
            true
          );
          setFinalResult(result);
          return;
        }

        // For streaming endpoints, simulate real-time updates
        if (endpoint.operationId === "async_monitor") {
          await handleMonitoringStream(body, customQueryParams);
        } else if (endpoint.operationId === "async_simulation") {
          await handleSimulationStream(body, customQueryParams);
        } else {
          // Default async handling
          addUpdate({
            status: "starting",
            message: "Starting async operation...",
          });
          const result = await executeEndpoint(body, customQueryParams);
          addUpdate({ status: "completed", result }, undefined, true);
          setFinalResult(result);
        }
      } catch (err) {
        const error = err as Error;
        setError(error);
        if (onError) onError(error);
      } finally {
        setIsStreaming(false);
      }
    },
    [
      endpoint,
      isStreamingEndpoint,
      executeEndpoint,
      addUpdate,
      onError,
      handleMonitoringStream,
      handleSimulationStream,
    ]
  );

  // Auto-execute on mount for GET requests
  useEffect(() => {
    if (endpoint.method === "GET") {
      startStreaming();
    }
  }, [endpoint.operationId, endpoint.method, startStreaming]);

  if (error) {
    return (
      <div style={{ padding: "20px", color: "#dc3545" }}>
        <h3>❌ Error</h3>
        <p>{error.message}</p>
        <button
          onClick={() => startStreaming()}
          style={{
            backgroundColor: "#007bff",
            color: "white",
            border: "none",
            padding: "8px 16px",
            borderRadius: "4px",
            cursor: "pointer",
          }}
        >
          🔄 Retry
        </button>
      </div>
    );
  }

  return (
    <div
      style={{
        padding: "20px",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}
    >
      {/* Header */}
      <div style={{ marginBottom: "20px" }}>
        <h2>{endpoint.summary || `${endpoint.method} ${endpoint.path}`}</h2>
        {isStreamingEndpoint && (
          <div
            style={{
              backgroundColor: "#e3f2fd",
              padding: "10px",
              borderRadius: "4px",
              marginBottom: "10px",
            }}
          >
            🔄 <strong>Streaming Endpoint:</strong> This endpoint supports
            real-time updates
          </div>
        )}
      </div>

      {/* Controls */}
      <div style={{ marginBottom: "20px" }}>
        {!isStreaming ? (
          <button
            onClick={() => startStreaming()}
            style={{
              backgroundColor: "#28a745",
              color: "white",
              border: "none",
              padding: "10px 20px",
              borderRadius: "4px",
              cursor: "pointer",
              marginRight: "10px",
            }}
          >
            ▶️ Start {isStreamingEndpoint ? "Streaming" : "Execution"}
          </button>
        ) : (
          <button
            onClick={() => setIsStreaming(false)}
            style={{
              backgroundColor: "#dc3545",
              color: "white",
              border: "none",
              padding: "10px 20px",
              borderRadius: "4px",
              cursor: "pointer",
              marginRight: "10px",
            }}
          >
            ⏹️ Stop Streaming
          </button>
        )}

        <span style={{ color: "#666", fontSize: "14px" }}>
          {isStreaming ? "🔴 Live" : "⚪ Stopped"} | Updates: {updates.length} |
          Status: {isStreaming ? "Streaming..." : "Ready"}
        </span>
      </div>

      {/* Live Updates Stream */}
      {updates.length > 0 && (
        <div style={{ marginBottom: "20px" }}>
          <h3>📊 Live Updates</h3>
          <div
            style={{
              maxHeight: "400px",
              overflowY: "auto",
              border: "1px solid #ddd",
              borderRadius: "4px",
              backgroundColor: "#f8f9fa",
            }}
          >
            {updates.map((update, index) => (
              <div
                key={update.id}
                style={{
                  padding: "10px",
                  borderBottom:
                    index < updates.length - 1 ? "1px solid #eee" : "none",
                  backgroundColor: update.isComplete ? "#d4edda" : "#fff3cd",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "5px",
                  }}
                >
                  <strong>
                    {update.step
                      ? `Step ${update.step}`
                      : `Update #${index + 1}`}
                    {update.isComplete && " ✅"}
                  </strong>
                  <small style={{ color: "#666" }}>
                    {new Date(update.timestamp).toLocaleTimeString()}
                  </small>
                </div>
                <pre
                  style={{
                    margin: 0,
                    fontSize: "12px",
                    backgroundColor: "rgba(0,0,0,0.05)",
                    padding: "8px",
                    borderRadius: "3px",
                    whiteSpace: "pre-wrap",
                    maxHeight: "100px",
                    overflowY: "auto",
                  }}
                >
                  {JSON.stringify(update.data, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Final Result */}
      {finalResult && (
        <div>
          <h3>🎯 Final Result</h3>
          <div
            style={{
              backgroundColor: "#d4edda",
              border: "1px solid #c3e6cb",
              borderRadius: "4px",
              padding: "15px",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "10px",
              }}
            >
              <span
                style={{
                  backgroundColor: getStatusColor(
                    finalResult.status_code || 200
                  ),
                  color: "white",
                  padding: "4px 8px",
                  borderRadius: "4px",
                  fontSize: "12px",
                  fontWeight: "bold",
                }}
              >
                {finalResult.status_code || 200}
              </span>
              <small style={{ color: "#666" }}>
                Completed at {new Date().toLocaleTimeString()}
              </small>
            </div>
            <pre
              style={{
                margin: 0,
                fontSize: "12px",
                backgroundColor: "rgba(0,0,0,0.05)",
                padding: "10px",
                borderRadius: "4px",
                whiteSpace: "pre-wrap",
                maxHeight: "300px",
                overflowY: "auto",
              }}
            >
              {JSON.stringify(finalResult, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* No data message */}
      {updates.length === 0 && !finalResult && !isStreaming && (
        <div
          style={{
            textAlign: "center",
            color: "#666",
            padding: "40px",
            backgroundColor: "#f8f9fa",
            borderRadius: "4px",
          }}
        >
          <p>
            Click "Start {isStreamingEndpoint ? "Streaming" : "Execution"}" to
            begin
          </p>
        </div>
      )}
    </div>
  );
};
