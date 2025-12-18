import React, { useCallback, useState, useReducer, useRef } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';

import { PyodideEndpoint, pyodideEngine } from './index';
import { EndpointComponentProps } from './types';
import { extractPathParams } from './utils';

interface RealStreamingComponentProps extends EndpointComponentProps {
  endpoint: PyodideEndpoint;
}

interface StreamMessage {
  id: string;
  timestamp: string;
  data: Record<string, unknown>;
  type?: string;
}

// Component for REAL Server-Sent Events streaming
export const RealStreamingComponent: React.FC<RealStreamingComponentProps> = ({ 
  endpoint, 
  onError 
}) => {
  const params = useParams();
  const [searchParams] = useSearchParams();
  const [messages, setMessages] = useState<StreamMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [metadata, setMetadata] = useState<Record<string, unknown> | null>(null);
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [, forceUpdate] = useReducer(x => x + 1, 0); // Force re-render mechanism
  
  // Use refs to maintain current state across async operations (avoids closure issues)
  const messagesRef = useRef<StreamMessage[]>([]);
  const metadataRef = useRef<Record<string, unknown> | null>(null);
  const summaryRef = useRef<Record<string, unknown> | null>(null);

  // Check if this endpoint supports SSE streaming
  const isSSEEndpoint = endpoint.operationId.includes('stream') || 
                        endpoint.path.includes('stream') ||
                        endpoint.path.includes('events');
  
  // Debug: Log render with current state
  console.log(`🎨 RealStreamingComponent rendering: ${messages.length} messages, metadata: ${!!metadata}, summary: ${!!summary}, streaming: ${isStreaming}`);

  const startStreaming = useCallback(async () => {
    try {
      setIsStreaming(true);
      setError(null);
      setMessages([]);
      setMetadata(null);
      setSummary(null);
      
      // Reset refs too
      messagesRef.current = [];
      metadataRef.current = null;
      summaryRef.current = null;

      if (!isSSEEndpoint) {
        throw new Error('This endpoint does not support SSE streaming');
      }

      console.log('🌊 Attempting TRUE real-time streaming for:', endpoint.operationId);

      // Convert params
      const queryParams: Record<string, string> = {};
      Array.from(searchParams.entries()).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
          queryParams[key] = String(value);
        }
      });

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

      // Buffer for parsing SSE format
      let buffer = '';

      // Build headers (including Authorization if available)
      const requestHeaders: Record<string, string> = {};
      const token = localStorage.getItem('access_token');
      if (token && token !== 'null') {
        requestHeaders['Authorization'] = `Bearer ${token}`;
      }

      try {
        // Try TRUE streaming execution - each chunk arrives and displays in real-time!
        console.log('🔄 Trying TRUE streaming mode...');
        
        await (pyodideEngine as any).endpointExecutor.executeEndpointStreaming(
          endpoint.operationId,
          async (chunkBytes: Uint8Array) => {
          // This callback is called for EACH chunk as it's generated!
          console.log(`📨 Real-time chunk: ${chunkBytes.byteLength} bytes`);
          
          // Decode chunk
          const text = new TextDecoder().decode(chunkBytes);
          console.log(`📄 Decoded text (${text.length} chars):`, text.substring(0, 100));
          buffer += text;

          // Parse complete SSE messages from buffer
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';
          console.log(`📋 Processing ${lines.length} lines, buffer remaining: ${buffer.length} chars`);

          let currentData = '';
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              currentData += line.substring(6);
              console.log(`📦 Data line found, accumulated: ${currentData.length} chars`);
            } else if (line.startsWith('event: ')) {
              const eventType = line.substring(7);
              console.log(`📡 Event type: ${eventType}`);
              if (eventType === 'close') {
                return;
              }
            } else if (line === '' && currentData) {
              console.log(`🔍 Attempting to parse: "${currentData.substring(0, 50)}..."`);
              try {
                const parsedData = JSON.parse(currentData);
                const msgType = parsedData.type || 'data';
                console.log(`✨ Parsed successfully: type=${msgType}`);

                const message: StreamMessage = {
                  id: `msg-${Date.now()}-${Math.random()}`,
                  timestamp: new Date().toISOString(),
                  data: parsedData,
                  type: msgType
                };

                // Display IMMEDIATELY - no delays!
                // Update BOTH ref (for async consistency) AND state (for React rendering)
                if (msgType === 'metadata') {
                  console.log(`📋 Setting metadata:`, parsedData);
                  metadataRef.current = parsedData;
                  setMetadata(parsedData);
                  console.log(`✅ Metadata set in ref and state`);
                } else if (msgType === 'complete') {
                  console.log(`✅ Setting summary:`, parsedData);
                  summaryRef.current = parsedData;
                  setSummary(parsedData);
                  
                  // Add complete message
                  messagesRef.current = [...messagesRef.current, message];
                  setMessages([...messagesRef.current]);
                  console.log(`📊 Complete added, total: ${messagesRef.current.length}`);
                } else {
                  console.log(`📨 Adding ${msgType} message`);
                  
                  // Update ref first (truth source)
                  messagesRef.current = [...messagesRef.current, message];
                  console.log(`📊 Ref updated: ${messagesRef.current.length} messages`);
                  
                  // Update state (triggers render)
                  setMessages([...messagesRef.current]);
                  console.log(`📊 State updated: ${messagesRef.current.length} messages`);
                }

                // Force re-render to ensure UI updates
                forceUpdate();
                
                console.log(`✅ Real-time display: ${msgType}, ref has ${messagesRef.current.length} messages`);
              } catch (err) {
                console.error('❌ Parse error for:', currentData, err);
              }
              currentData = '';
            } else if (line !== '') {
              console.log(`⚠️ Unhandled line: "${line}"`);
            }
          }
        },
          pathParams,
          queryParams,
          undefined,
          requestHeaders
        );

        console.log('🎉 TRUE streaming complete!');
      
      // CRITICAL: Use queueMicrotask to sync state AFTER current async task
      await new Promise(resolve => {
        queueMicrotask(() => {
          console.log(`🔄 Syncing final state: ${messagesRef.current.length} messages`);
          setMessages([...messagesRef.current]);
          setMetadata(metadataRef.current);
          setSummary(summaryRef.current);
          resolve(undefined);
        });
      });
      
      // Force one more update
      forceUpdate();
      
      // Give React's scheduler time to process
      await new Promise(resolve => setTimeout(resolve, 50));
      console.log(`📊 Final state: ${messagesRef.current.length} messages (ref), UI should show ${messagesRef.current.length}`);

      } catch (streamErr) {
        // If streaming fails (e.g., endpoint doesn't return StreamingResponse),
        // fall back to regular execution with simulated streaming
        const errMsg = streamErr instanceof Error ? streamErr.message : String(streamErr);
        
        if (errMsg.includes('Not a StreamingResponse') || errMsg.includes('Endpoint not found')) {
          console.log('⚠️ Not a streaming endpoint, falling back to regular execution...');
          
          // Execute as regular endpoint and parse response
          const result = await pyodideEngine.executeEndpoint(
            endpoint.operationId,
            pathParams,
            queryParams,
            undefined
          ) as any;

          console.log('📦 Received response (fallback mode):', result);

          // Display as single message or parse structured response
          if (result.content && typeof result.content === 'object') {
            const message: StreamMessage = {
              id: `msg-${Date.now()}`,
              timestamp: new Date().toISOString(),
              data: result.content,
              type: 'data'
            };
            setMessages([message]);
            setSummary({ type: 'complete' });
          } else if (result.content) {
            const message: StreamMessage = {
              id: `msg-${Date.now()}`,
              timestamp: new Date().toISOString(),
              data: { result: result.content },
              type: 'data'
            };
            setMessages([message]);
          }
        } else {
          throw streamErr; // Re-throw if it's a different error
        }
      }

    } catch (err) {
      const error = err as Error;
      console.error('❌ Stream error:', error);
      setError(error);
      if (onError) onError(error);
    } finally {
      setIsStreaming(false);
    }
  }, [endpoint, params, searchParams, isSSEEndpoint, onError]);

  const stopStreaming = useCallback(() => {
    setIsStreaming(false);
  }, []);

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
            cursor: "pointer"
          }}
        >
          🔄 Retry
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: "20px", fontFamily: "system-ui, -apple-system, sans-serif" }}>
      {/* Header */}
      <div style={{ marginBottom: "20px" }}>
        <h2>{endpoint.summary || `${endpoint.method} ${endpoint.path}`}</h2>
        {isSSEEndpoint ? (
          <div style={{ 
            backgroundColor: "#e3f2fd", 
            padding: "10px", 
            borderRadius: "4px",
            marginBottom: "10px"
          }}>
            🌊 <strong>Server-Sent Events (SSE):</strong> This endpoint uses REAL streaming (data sent as it's generated)
          </div>
        ) : (
          <div style={{ 
            backgroundColor: "#fff3cd", 
            padding: "10px", 
            borderRadius: "4px",
            marginBottom: "10px"
          }}>
            ⚠️ <strong>Not an SSE endpoint:</strong> This endpoint does not support real streaming
          </div>
        )}
      </div>

      {/* Metadata */}
      {metadata && (
        <div style={{ marginBottom: "20px" }}>
          <h3>ℹ️ Stream Metadata</h3>
          <div style={{
            backgroundColor: "#e7f3ff",
            border: "1px solid #b3d7ff",
            borderRadius: "4px",
            padding: "12px"
          }}>
            <pre style={{
              margin: 0,
              fontSize: "12px",
              whiteSpace: "pre-wrap"
            }}>
              {JSON.stringify(metadata, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Controls */}
      <div style={{ marginBottom: "20px" }}>
        {!isStreaming ? (
          <button
            onClick={() => startStreaming()}
            disabled={!isSSEEndpoint}
            style={{
              backgroundColor: isSSEEndpoint ? "#28a745" : "#6c757d",
              color: "white",
              border: "none",
              padding: "10px 20px",
              borderRadius: "4px",
              cursor: isSSEEndpoint ? "pointer" : "not-allowed",
              marginRight: "10px"
            }}
          >
            ▶️ Start Real Streaming
          </button>
        ) : (
          <button
            onClick={stopStreaming}
            style={{
              backgroundColor: "#dc3545",
              color: "white",
              border: "none",
              padding: "10px 20px",
              borderRadius: "4px",
              cursor: "pointer",
              marginRight: "10px"
            }}
          >
            ⏹️ Stop Streaming
          </button>
        )}
        
        <span style={{ color: "#666", fontSize: "14px" }}>
          {isStreaming ? "🔴 Live" : "⚪ Stopped"} | 
          Messages: {messages.length} | 
          Status: {isStreaming ? "Streaming..." : "Ready"}
        </span>
      </div>

      {/* Live Messages Stream */}
      {messages.length > 0 && (
        <div style={{ marginBottom: "20px" }}>
          <h3>📊 Live Stream ({messages.length} messages)</h3>
          <div 
            style={{ 
              maxHeight: "500px", 
              overflowY: "auto", 
              border: "1px solid #ddd",
              borderRadius: "4px",
              backgroundColor: "#f8f9fa"
            }}
          >
            {messages.map((message, index) => (
              <div
                key={message.id}
                style={{
                  padding: "10px",
                  borderBottom: index < messages.length - 1 ? "1px solid #eee" : "none",
                  backgroundColor: message.type === 'complete' ? "#d4edda" : 
                                   message.type === 'metadata' ? "#e7f3ff" : "#fff"
                }}
              >
                <div style={{ 
                  display: "flex", 
                  justifyContent: "space-between", 
                  alignItems: "center",
                  marginBottom: "5px"
                }}>
                  <strong>
                    {message.type === 'metadata' && '📋 Metadata'}
                    {message.type === 'step' && `🔄 Step ${(message.data as any).step}`}
                    {message.type === 'iteration' && `🔄 Iteration ${(message.data as any).iteration}`}
                    {message.type === 'complete' && '✅ Complete'}
                    {!message.type && `Message #${index + 1}`}
                  </strong>
                  <small style={{ color: "#666" }}>
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </small>
                </div>
                <pre style={{ 
                  margin: 0, 
                  fontSize: "12px", 
                  backgroundColor: "rgba(0,0,0,0.05)",
                  padding: "8px",
                  borderRadius: "3px",
                  whiteSpace: "pre-wrap",
                  maxHeight: "150px",
                  overflowY: "auto"
                }}>
                  {JSON.stringify(message.data, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Summary */}
      {summary && !isStreaming && (
        <div>
          <h3>🎯 Stream Summary</h3>
          <div style={{
            backgroundColor: "#d4edda",
            border: "1px solid #c3e6cb",
            borderRadius: "4px",
            padding: "15px"
          }}>
            <pre style={{
              margin: 0,
              fontSize: "12px",
              backgroundColor: "rgba(0,0,0,0.05)",
              padding: "10px",
              borderRadius: "4px",
              whiteSpace: "pre-wrap"
            }}>
              {JSON.stringify(summary, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* No data message */}
      {messages.length === 0 && !isStreaming && (
        <div style={{ 
          textAlign: "center", 
          color: "#666", 
          padding: "40px",
          backgroundColor: "#f8f9fa",
          borderRadius: "4px"
        }}>
          <p>
            {isSSEEndpoint 
              ? 'Click "Start Real Streaming" to begin receiving live updates'
              : 'This endpoint does not support Server-Sent Events'}
          </p>
        </div>
      )}
    </div>
  );
};

