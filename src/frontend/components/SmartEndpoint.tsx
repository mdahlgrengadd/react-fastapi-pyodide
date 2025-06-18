import React from 'react';
import { useSearchParams } from 'react-router-dom';

import { PyodideEndpointComponent } from './EndpointComponent';
import { PyodideEndpoint } from './index';
import { EndpointComponentProps } from './types';

interface SmartEndpointProps extends EndpointComponentProps {
  endpoints: PyodideEndpoint[];
}

// Smart component that uses query parameters to determine HTTP method
export const SmartEndpoint: React.FC<SmartEndpointProps> = ({
  endpoints,
  onError,
}) => {
  const [searchParams] = useSearchParams();
  const requestedMethod = searchParams.get("method")?.toUpperCase() || "GET";

  // Find the endpoint for the requested method, fallback to GET, then first available
  const selectedEndpoint =
    endpoints.find((ep) => ep.method === requestedMethod) ||
    endpoints.find((ep) => ep.method === "GET") ||
    endpoints[0];

  return (
    <div
      style={{
        padding: "20px",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}
    >
      {/* Render the selected endpoint */}
      <PyodideEndpointComponent endpoint={selectedEndpoint} onError={onError} />
    </div>
  );
};
