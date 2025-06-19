import React from "react";
import { useSearchParams } from "react-router-dom";

import { PyodideEndpointComponent } from "./EndpointComponent";
import { PyodideEndpoint } from "./index";
import { StreamingEndpointComponent } from "./StreamingEndpointComponent";
import { EndpointComponentProps } from "./types";

interface SmartEndpointProps extends EndpointComponentProps {
  endpoints: PyodideEndpoint[];
  forceStreaming?: boolean; // Force streaming mode
}

// Smart component that automatically chooses between regular and streaming components
export const SmartEndpoint: React.FC<SmartEndpointProps> = ({
  endpoints,
  onError,
  forceStreaming = false,
}) => {
  const [searchParams] = useSearchParams();
  const requestedMethod = searchParams.get("method")?.toUpperCase() || "GET";
  const streamingMode =
    searchParams.get("streaming") === "true" || forceStreaming;

  // Find the endpoint for the requested method, fallback to GET, then first available
  const selectedEndpoint =
    endpoints.find((ep) => ep.method === requestedMethod) ||
    endpoints.find((ep) => ep.method === "GET") ||
    endpoints[0];

  // Check if this endpoint should use streaming
  const useStreaming =
    streamingMode ||
    selectedEndpoint.operationId.includes("async") ||
    selectedEndpoint.operationId.includes("monitor") ||
    selectedEndpoint.operationId.includes("stream") ||
    selectedEndpoint.operationId.includes("workflow");

  return (
    <div
      style={{
        padding: "20px",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}
    >
      {/* Show component selection info */}
      <div
        style={{
          marginBottom: "15px",
          padding: "10px",
          backgroundColor: useStreaming ? "#e3f2fd" : "#f8f9fa",
          borderRadius: "4px",
          border: "1px solid " + (useStreaming ? "#bbdefb" : "#dee2e6"),
        }}
      >
        <div style={{ fontSize: "14px", color: "#666" }}>
          <strong>Component Mode:</strong>{" "}
          {useStreaming ? "🔄 Streaming" : "⚡ Standard"} |
          <strong> Endpoint:</strong> {selectedEndpoint.operationId} |
          <strong> Method:</strong> {selectedEndpoint.method}
        </div>
        {useStreaming && (
          <div style={{ fontSize: "12px", color: "#1976d2", marginTop: "5px" }}>
            📊 This endpoint will show real-time updates and progressive results
          </div>
        )}
      </div>

      {/* Render the appropriate component */}
      {useStreaming ? (
        <StreamingEndpointComponent
          endpoint={selectedEndpoint}
          onError={onError}
        />
      ) : (
        <PyodideEndpointComponent
          endpoint={selectedEndpoint}
          onError={onError}
        />
      )}

      {/* Component toggle controls */}
      <div
        style={{
          marginTop: "20px",
          padding: "10px",
          backgroundColor: "#f8f9fa",
          borderRadius: "4px",
          fontSize: "14px",
        }}
      >
        <strong>💡 Pro Tip:</strong> Add <code>?streaming=true</code> to the URL
        to force streaming mode for any endpoint, or{" "}
        <code>?streaming=false</code> to use standard mode.
      </div>
    </div>
  );
};
