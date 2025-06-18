import "../../index.css";

import React, { lazy, Suspense } from "react";

// Lazy load PyodideFileApp for better performance
const PyodideFileApp = lazy(() =>
  import("../../components").then((module) => ({
    default: module.PyodideFileApp,
  }))
);

// Loading fallback component
const LoadingFallback: React.FC = () => (
  <div className="flex items-center justify-center min-h-screen bg-gray-50">
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
      <h2 className="text-xl font-semibold text-gray-700 mb-2">
        Loading Python Environment
      </h2>
      <p className="text-sm text-gray-500">
        Initializing Pyodide and FastAPI...
      </p>
    </div>
  </div>
);

const App: React.FC = () => {
  return (
    <Suspense fallback={<LoadingFallback />}>
      {" "}
      <PyodideFileApp
        // Use the new modular API structure
        pythonFile="/backend/v1/main.py" // New structured API with proper imports
        // pythonFile="/pyodide-demo.py" // Legacy monolithic file (if it existed)
        // pythonFile="/my-custom-api.py"    // Your own custom API
        enableDevTools={true}
        onError={(error) => {
          console.error("Pyodide App Error:", error);
        }}
        onLoading={(loading) => {
          console.log(`Pyodide App Loading: ${loading}`);
        }}
      />
    </Suspense>
  );
};

export default App;
