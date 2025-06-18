import React from 'react';
import { Link } from 'react-router-dom';

import { PyodideEndpoint, pyodideEngine } from './index';
import { convertOpenAPIPathToReactRouter, getMethodColor } from './utils';

interface EndpointListProps {
  endpoints: PyodideEndpoint[];
}

export const EndpointList: React.FC<EndpointListProps> = ({ endpoints }) => {
  const groupedEndpoints = endpoints.reduce((acc, endpoint) => {
    const category = endpoint.path.startsWith("/users")
      ? "User Management"
      : "General";
    if (!acc[category]) acc[category] = [];
    acc[category].push(endpoint);
    return acc;
  }, {} as Record<string, PyodideEndpoint[]>);

  return (
    <div
      style={{
        padding: "20px",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}
    >
      <div
        style={{
          marginBottom: "30px",
          padding: "20px",
          background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
          borderRadius: "12px",
          textAlign: "center",
          color: "white",
        }}
      >
        <h1 style={{ margin: "0 0 10px 0", fontSize: "2.5em" }}>
          🐍 Pyodide FastAPI Demo
        </h1>
        <p style={{ margin: "0 0 15px 0", fontSize: "1.2em", opacity: 0.9 }}>
          Real Python FastAPI running in your browser via Pyodide!
        </p>
        <div
          style={{
            display: "inline-block",
            backgroundColor: "rgba(255,255,255,0.2)",
            padding: "10px 20px",
            borderRadius: "25px",
            fontSize: "14px",
          }}
        >
          ✨ Full CRUD Operations • 🔍 Search & Filter • 📊 Statistics • 🚀 Zero
          Server Required
        </div>
      </div>

      {Object.entries(groupedEndpoints).map(([category, categoryEndpoints]) => (
        <div key={category} style={{ marginBottom: "30px" }}>
          <h2
            style={{
              color: "#495057",
              borderBottom: "2px solid #dee2e6",
              paddingBottom: "10px",
              marginBottom: "20px",
            }}
          >
            {category === "User Management" ? "👥" : "⚙️"} {category}
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
              gap: "15px",
            }}
          >
            {categoryEndpoints.map((endpoint) => {
              const routePath = convertOpenAPIPathToReactRouter(endpoint.path);

              // For endpoints with path parameters, provide sample values
              let demoPath = routePath;
              if (endpoint.path.includes("{user_id}")) {
                demoPath = routePath.replace(":user_id", "1"); // Use sample user ID
              }

              const linkPath =
                endpoint.method === "GET"
                  ? demoPath
                  : `${demoPath}?method=${endpoint.method.toLowerCase()}`;

              return (
                <Link
                  key={endpoint.operationId}
                  to={linkPath}
                  style={{
                    textDecoration: "none",
                    display: "block",
                    padding: "20px",
                    backgroundColor: "#ffffff",
                    borderRadius: "8px",
                    border: "1px solid #dee2e6",
                    boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
                    transition: "all 0.2s ease",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = "translateY(-2px)";
                    e.currentTarget.style.boxShadow =
                      "0 4px 8px rgba(0,0,0,0.15)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = "translateY(0)";
                    e.currentTarget.style.boxShadow =
                      "0 2px 4px rgba(0,0,0,0.1)";
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      marginBottom: "10px",
                    }}
                  >
                    <span
                      style={{
                        backgroundColor: getMethodColor(endpoint.method),
                        color: endpoint.method === "PUT" ? "#212529" : "white",
                        padding: "4px 8px",
                        borderRadius: "4px",
                        fontSize: "12px",
                        fontWeight: "600",
                        marginRight: "10px",
                        minWidth: "60px",
                        textAlign: "center",
                      }}
                    >
                      {endpoint.method}
                    </span>
                    <code
                      style={{
                        backgroundColor: "#f8f9fa",
                        padding: "4px 8px",
                        borderRadius: "4px",
                        fontSize: "13px",
                        color: "#495057",
                      }}
                    >
                      {endpoint.path}
                    </code>
                  </div>
                  {endpoint.summary && (
                    <p
                      style={{
                        margin: "0",
                        color: "#6c757d",
                        fontSize: "14px",
                        lineHeight: "1.4",
                      }}
                    >
                      {endpoint.summary}
                    </p>
                  )}
                </Link>
              );
            })}
          </div>
        </div>
      ))}

      <div
        style={{
          marginTop: "40px",
          padding: "20px",
          backgroundColor: "#f8f9fa",
          borderRadius: "8px",
          border: "1px solid #dee2e6",
        }}
      >
        <h3 style={{ marginTop: 0, color: "#495057" }}>📚 API Documentation</h3>
        <p style={{ color: "#6c757d", marginBottom: "15px" }}>
          Explore the API with interactive documentation powered by Swagger UI.
        </p>
        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <Link
            to="/docs"
            style={{
              padding: "10px 20px",
              backgroundColor: "#2196f3",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
              fontSize: "14px",
              fontWeight: "500",
              textDecoration: "none",
              display: "inline-block",
            }}
          >
            📖 Open Swagger UI
          </Link>
          <button
            onClick={() => {
              const schema = pyodideEngine.getOpenAPISchema();
              console.log("OpenAPI Schema:", schema);
              alert(
                "OpenAPI schema logged to console! Check the browser developer tools."
              );
            }}
            style={{
              padding: "10px 20px",
              backgroundColor: "#4CAF50",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
              fontSize: "14px",
              fontWeight: "500",
            }}
          >
            🔍 Show OpenAPI Schema
          </button>
        </div>
      </div>
    </div>
  );
};
