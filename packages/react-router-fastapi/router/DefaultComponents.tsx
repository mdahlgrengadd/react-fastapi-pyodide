// filepath: d:\react-router-fastapi\src\lib\react-router-fastapi\router\DefaultComponents.tsx
import React from "react";

export const DefaultLoading: React.FC = () => (
  <div
    style={{
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      height: "200px",
      fontSize: "16px",
      color: "#666",
    }}
  >
    <div>Loading...</div>
  </div>
);

export const DefaultError: React.FC<{ error: Error }> = ({ error }) => (
  <div
    style={{
      padding: "20px",
      backgroundColor: "#fee",
      border: "1px solid #fcc",
      borderRadius: "4px",
      color: "#c33",
      margin: "20px",
    }}
  >
    <h3>Error</h3>
    <p>{error.message}</p>
    {process.env.NODE_ENV === "development" && (
      <details style={{ marginTop: "10px" }}>
        <summary>Stack trace</summary>
        <pre style={{ fontSize: "12px", overflow: "auto" }}>{error.stack}</pre>
      </details>
    )}
  </div>
);
