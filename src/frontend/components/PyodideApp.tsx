import React from "react";
import { RouterProvider } from "react-router-dom";

import { PyodideProvider, usePyodide } from "./Context";

// Loading component for the entire app
const PyodideAppLoading: React.FC = () => {
  const [loadingMessage, setLoadingMessage] = React.useState(
    " Initializing Pyodide..."
  );

  React.useEffect(() => {
    const messages = [
      " Initializing Pyodide...",
      " Loading Python packages...",
      " Setting up FastAPI framework...",
      " Almost ready...",
    ];

    let messageIndex = 0;
    const interval = setInterval(() => {
      messageIndex = (messageIndex + 1) % messages.length;
      setLoadingMessage(messages[messageIndex]);
    }, 1500);

    return () => clearInterval(interval);
  }, []);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100vh",
        backgroundColor: "#f5f5f5",
      }}
    >
      <div
        style={{
          padding: "40px",
          backgroundColor: "white",
          borderRadius: "10px",
          boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
          textAlign: "center",
          maxWidth: "400px",
        }}
      >
        <div style={{ fontSize: "24px", marginBottom: "20px" }}>
          {loadingMessage}
        </div>

        <div
          style={{
            width: "100%",
            height: "4px",
            backgroundColor: "#e0e0e0",
            borderRadius: "2px",
            overflow: "hidden",
            marginBottom: "15px",
          }}
        >
          <div
            style={{
              width: "100%",
              height: "100%",
              backgroundColor: "#2196f3",
              borderRadius: "2px",
              animation: "loading 2s ease-in-out infinite",
            }}
          />
        </div>

        <div style={{ fontSize: "14px", color: "#666", lineHeight: "1.5" }}>
          <div>
            <strong>One-time setup:</strong> Pyodide loads only once
          </div>
          <div>
            <strong>Smart caching:</strong> Python code cached automatically
          </div>
          <div>
            <strong>Persistent routes:</strong> Navigation stays instant
          </div>
        </div>
      </div>

      <style>{`
        @keyframes loading {
          0% { transform: translateX(-100%); }
          50% { transform: translateX(0%); }
          100% { transform: translateX(100%); }
        }
      `}</style>
    </div>
  );
};

// Error component
const PyodideAppError: React.FC<{ error: Error }> = ({ error }) => (
  <div
    style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      height: "100vh",
      backgroundColor: "#f5f5f5",
      padding: "20px",
    }}
  >
    <div
      style={{
        padding: "30px",
        backgroundColor: "white",
        borderRadius: "10px",
        boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
        textAlign: "center",
        maxWidth: "500px",
        border: "2px solid #f44336",
      }}
    >
      <h2 style={{ color: "#f44336", marginBottom: "15px" }}>
        Pyodide Initialization Error
      </h2>
      <p style={{ marginBottom: "15px", color: "#666" }}>
        Failed to initialize Pyodide or load your Python code.
      </p>
      <pre
        style={{
          backgroundColor: "#f5f5f5",
          padding: "15px",
          borderRadius: "5px",
          textAlign: "left",
          overflow: "auto",
          fontSize: "12px",
        }}
      >
        {error.message}
      </pre>
      <button
        onClick={() => window.location.reload()}
        style={{
          marginTop: "15px",
          padding: "10px 20px",
          backgroundColor: "#2196f3",
          color: "white",
          border: "none",
          borderRadius: "5px",
          cursor: "pointer",
        }}
      >
        Reload Page
      </button>
    </div>
  </div>
);

// Inner component that consumes the context
const PyodideAppInner: React.FC = () => {
  const { isLoading, error, router } = usePyodide();

  if (isLoading) {
    return <PyodideAppLoading />;
  }

  if (error) {
    return <PyodideAppError error={error} />;
  }

  if (!router) {
    return <div>No router available</div>;
  }

  return <RouterProvider router={router} />;
};

// Main PyodideApp component
interface PyodideAppProps {
  pythonCode: string;
  enableDevTools?: boolean;
  onError?: (error: Error) => void;
}

export const PyodideApp: React.FC<PyodideAppProps> = (props) => {
  return (
    <PyodideProvider {...props}>
      <PyodideAppInner />
    </PyodideProvider>
  );
};
