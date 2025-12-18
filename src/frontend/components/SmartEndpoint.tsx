import React from 'react';
import { useSearchParams } from 'react-router-dom';

import { PyodideEndpointComponent } from './EndpointComponent';
import { StreamingEndpointComponent } from './StreamingEndpointComponent';
import { RealStreamingComponent } from './RealStreamingComponent';
import { PyodideEndpoint } from './index';
import { EndpointComponentProps } from './types';

interface SmartEndpointProps extends EndpointComponentProps {
  endpoints: PyodideEndpoint[];
  forceStreaming?: boolean; // Force streaming mode
  forceSSE?: boolean; // Force SSE real streaming
}

// Smart component that automatically chooses between regular, simulated streaming, and real SSE streaming
export const SmartEndpoint: React.FC<SmartEndpointProps> = ({
  endpoints,
  onError,
  forceStreaming = false,
  forceSSE = false,
}) => {
  const [searchParams] = useSearchParams();
  const requestedMethod = searchParams.get("method")?.toUpperCase() || "GET";
  const streamingMode = searchParams.get("streaming") === "true" || forceStreaming;
  const sseMode = searchParams.get("sse") === "true" || forceSSE;

  // Find the endpoint for the requested method, fallback to GET, then first available
  const selectedEndpoint =
    endpoints.find((ep) => ep.method === requestedMethod) ||
    endpoints.find((ep) => ep.method === "GET") ||
    endpoints[0];

  // Check if this endpoint supports real SSE streaming
  // Heuristic: Check for streaming indicators in path (more reliable than operation_id)
  const isSSEEndpoint = selectedEndpoint.path.includes('-stream') ||  // /async-monitor-stream
                        selectedEndpoint.path.includes('/events') ||  // /system/events
                        selectedEndpoint.path.endsWith('/stream');

  // Check if this endpoint should use simulated streaming
  const useSimulatedStreaming = (streamingMode || 
                                 selectedEndpoint.operationId.includes('async') ||
                                 selectedEndpoint.operationId.includes('monitor') ||
                                 selectedEndpoint.operationId.includes('workflow')) &&
                                !isSSEEndpoint;

  // Determine which component to use
  const useSSE = sseMode || isSSEEndpoint;
  const useStreaming = useSimulatedStreaming && !useSSE;

  // Determine the mode description
  let modeDescription = "⚡ Standard";
  let modeColor = "#f8f9fa";
  let modeBorder = "#dee2e6";
  if (useSSE) {
    modeDescription = "🌊 Real SSE Streaming";
    modeColor = "#e7f3ff";
    modeBorder = "#b3d7ff";
  } else if (useStreaming) {
    modeDescription = "🔄 Simulated Streaming";
    modeColor = "#e3f2fd";
    modeBorder = "#bbdefb";
  }

  return (
    <div
      style={{
        padding: "20px",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}
    >
      {/* Show component selection info */}
      <div style={{ 
        marginBottom: "15px", 
        padding: "10px", 
        backgroundColor: modeColor,
        borderRadius: "4px",
        border: "1px solid " + modeBorder
      }}>
        <div style={{ fontSize: "14px", color: "#666" }}>
          <strong>Component Mode:</strong> {modeDescription} | 
          <strong> Endpoint:</strong> {selectedEndpoint.operationId} | 
          <strong> Method:</strong> {selectedEndpoint.method}
        </div>
        {useSSE && (
          <div style={{ fontSize: "12px", color: "#0277bd", marginTop: "5px" }}>
            🌊 Server-Sent Events: Data streams in real-time as it's generated on the server
          </div>
        )}
        {useStreaming && !useSSE && (
          <div style={{ fontSize: "12px", color: "#1976d2", marginTop: "5px" }}>
            🔄 Simulated Streaming: Full response fetched, then displayed progressively
          </div>
        )}
      </div>

      {/* Render the appropriate component */}
      {useSSE ? (
        <RealStreamingComponent endpoint={selectedEndpoint} onError={onError} />
      ) : useStreaming ? (
        <StreamingEndpointComponent endpoint={selectedEndpoint} onError={onError} />
      ) : (
        <PyodideEndpointComponent endpoint={selectedEndpoint} onError={onError} />
      )}

      {/* Component toggle controls */}
      <div style={{ 
        marginTop: "20px", 
        padding: "10px", 
        backgroundColor: "#f8f9fa",
        borderRadius: "4px",
        fontSize: "14px"
      }}>
        <strong>💡 Pro Tip:</strong> Add <code>?streaming=true</code> for simulated streaming, 
        <code>?sse=true</code> for real SSE streaming, or <code>?streaming=false</code> for standard mode.
      </div>
    </div>
  );
};
