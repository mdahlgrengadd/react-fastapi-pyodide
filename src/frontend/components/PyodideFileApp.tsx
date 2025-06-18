import React, { useEffect, useState } from "react";

import { PyodideApp } from "./PyodideApp";

// Component that loads Python code from external files
interface PyodideFileAppProps {
  pythonFile: string; // Path to Python file (relative to public directory)
  enableDevTools?: boolean;
  onError?: (error: Error) => void;
  onLoading?: (loading: boolean) => void;
}

export const PyodideFileApp: React.FC<PyodideFileAppProps> = ({
  pythonFile,
  enableDevTools = process.env.NODE_ENV === "development",
  onError,
  onLoading,
}) => {
  const [pythonCode, setPythonCode] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const loadPythonFile = async () => {
      try {
        setLoading(true);
        setError(null);
        onLoading?.(true);

        console.log(` Loading Python file: ${pythonFile}`);

        // Construct the correct path considering the base URL
        const basePath = import.meta.env.BASE_URL || "/";
        const fullPath =
          basePath === "/"
            ? pythonFile
            : `${basePath.replace(/\/$/, "")}${pythonFile}`;

        console.log(` Full path: ${fullPath}`);

        // Fetch the Python file from the public directory
        const response = await fetch(fullPath);

        if (!response.ok) {
          throw new Error(
            `Failed to load Python file: ${response.status} ${response.statusText}`
          );
        }

        const code = await response.text();

        if (!code.trim()) {
          throw new Error("Python file is empty");
        }

        console.log(
          ` Python file loaded successfully (${code.length} characters)`
        );
        setPythonCode(code);
      } catch (err) {
        const error = err as Error;
        console.error(" Error loading Python file:", error);
        setError(error);
        onError?.(error);
      } finally {
        setLoading(false);
        onLoading?.(false);
      }
    };

    loadPythonFile();
  }, [pythonFile, onError, onLoading]);

  // Loading state
  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          backgroundColor: "#f5f5f5",
          fontFamily: "system-ui, -apple-system, sans-serif",
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
            Loading Python File...
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
              File: <code>{pythonFile}</code>
            </div>
            <div> Fetching from public directory...</div>
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
  }

  // Error state
  if (error) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          backgroundColor: "#f5f5f5",
          padding: "20px",
          fontFamily: "system-ui, -apple-system, sans-serif",
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
            File Loading Error
          </h2>
          <p style={{ marginBottom: "15px", color: "#666" }}>
            Failed to load Python file: <code>{pythonFile}</code>
          </p>
          <pre
            style={{
              backgroundColor: "#f5f5f5",
              padding: "15px",
              borderRadius: "5px",
              textAlign: "left",
              overflow: "auto",
              fontSize: "12px",
              marginBottom: "15px",
            }}
          >
            {error.message}
          </pre>
          <div
            style={{ fontSize: "14px", color: "#666", marginBottom: "15px" }}
          >
            <div>
              <strong>Tips:</strong>
            </div>
            <div>
              • Ensure the file exists in the <code>public/</code> directory
            </div>
            <div>• Check the file path is correct</div>
            <div>• Verify the development server is running</div>
          </div>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: "10px 20px",
              backgroundColor: "#2196f3",
              border: "none",
              borderRadius: "5px",
              cursor: "pointer",
              fontSize: "14px",
              fontWeight: "500",
            }}
          >
            Reload Page
          </button>
        </div>
      </div>
    );
  }

  // Success state - render the PyodideApp with loaded code
  if (pythonCode) {
    return (
      <PyodideApp
        pythonCode={pythonCode}
        enableDevTools={enableDevTools}
        onError={onError}
      />
    );
  }

  return null;
};
