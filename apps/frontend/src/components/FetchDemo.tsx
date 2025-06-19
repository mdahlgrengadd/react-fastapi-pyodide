import { useState } from 'react';

interface FetchDemoProps {
  isInterceptorActive: boolean;
}

export function FetchDemo({ isInterceptorActive }: FetchDemoProps) {
  const [results, setResults] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});

  const runTest = async (testName: string, testFn: () => Promise<any>) => {
    setLoading(prev => ({ ...prev, [testName]: true }));
    try {
      const result = await testFn();
      setResults(prev => ({ 
        ...prev, 
        [testName]: { 
          success: true, 
          data: result,
          timestamp: new Date().toISOString()
        } 
      }));
    } catch (error) {
      setResults(prev => ({ 
        ...prev, 
        [testName]: { 
          success: false, 
          error: error instanceof Error ? error.message : String(error),
          timestamp: new Date().toISOString()
        } 
      }));
    } finally {
      setLoading(prev => ({ ...prev, [testName]: false }));
    }
  };

  const tests = [
    {
      name: 'health-check',
      title: 'Health Check (GET)',
      description: 'fetch("/api/system/health")',
      run: () => fetch('/api/system/health').then(r => r.json())
    },
    {
      name: 'users-list',
      title: 'List Users (GET)',
      description: 'fetch("/api/users/")',
      run: () => fetch('/api/users/').then(r => r.json())
    },
    {
      name: 'posts-list',
      title: 'List Posts (GET)',
      description: 'fetch("/api/posts/")',
      run: () => fetch('/api/posts/').then(r => r.json())
    },
    {
      name: 'create-user',
      title: 'Create User (POST)',
      description: 'POST /api/users/ with JSON body',
      run: () => fetch('/api/users/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: `test-${Date.now()}@example.com`,
          full_name: 'Test User',
          is_active: true
        })
      }).then(r => r.json())
    },
    {
      name: 'dashboard-stats',
      title: 'Dashboard Stats (GET)',
      description: 'fetch("/api/dashboard/stats")',
      run: () => fetch('/api/dashboard/stats').then(r => r.json())
    }
  ];

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold text-gray-800">
          🚀 Fetch Interceptor Demo
        </h2>
        <div className="flex items-center space-x-2">
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            isInterceptorActive 
              ? 'bg-green-100 text-green-800' 
              : 'bg-red-100 text-red-800'
          }`}>
            {isInterceptorActive ? '✅ Interceptor Active' : '❌ Interceptor Inactive'}
          </span>
        </div>
      </div>

      <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
        <h3 className="font-semibold text-blue-800 mb-2">How it works:</h3>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>• All <code className="bg-blue-200 px-1 rounded">fetch()</code> calls to <code>/api/*</code> are automatically intercepted</li>
          <li>• Requests are routed through the Pyodide bridge instead of making HTTP calls</li>
          <li>• Responses are returned as standard <code className="bg-blue-200 px-1 rounded">Response</code> objects</li>
          <li>• Your existing code works without any modifications!</li>
        </ul>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {tests.map((test) => {
          const result = results[test.name];
          const isLoading = loading[test.name];
          
          return (
            <div key={test.name} className="border rounded-lg p-4">
              <div className="mb-3">
                <h3 className="font-semibold text-gray-800">{test.title}</h3>
                <code className="text-xs text-gray-600 bg-gray-100 px-2 py-1 rounded">
                  {test.description}
                </code>
              </div>
              
              <button
                onClick={() => runTest(test.name, test.run)}
                disabled={isLoading || !isInterceptorActive}
                className={`w-full px-3 py-2 rounded font-medium text-sm transition-colors ${
                  isLoading || !isInterceptorActive
                    ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700 text-white'
                }`}
              >
                {isLoading ? 'Running...' : 'Test'}
              </button>
              
              {result && (
                <div className={`mt-3 p-3 rounded text-xs ${
                  result.success 
                    ? 'bg-green-50 border border-green-200' 
                    : 'bg-red-50 border border-red-200'
                }`}>
                  <div className="flex justify-between items-center mb-2">
                    <span className={`font-semibold ${
                      result.success ? 'text-green-800' : 'text-red-800'
                    }`}>
                      {result.success ? '✅ Success' : '❌ Error'}
                    </span>
                    <span className="text-gray-500">
                      {new Date(result.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  
                  <pre className={`overflow-auto max-h-32 ${
                    result.success ? 'text-green-700' : 'text-red-700'
                  }`}>
                    {result.success 
                      ? JSON.stringify(result.data, null, 2)
                      : result.error
                    }
                  </pre>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-6 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
        <h3 className="font-semibold text-yellow-800 mb-2">💡 Pro Tips:</h3>
        <ul className="text-sm text-yellow-700 space-y-1">
          <li>• Use with existing libraries like <code className="bg-yellow-200 px-1 rounded">axios</code>, <code className="bg-yellow-200 px-1 rounded">ky</code>, etc.</li>
          <li>• Works with React Query, SWR, and other data fetching libraries</li>
          <li>• Supports all HTTP methods (GET, POST, PUT, DELETE, etc.)</li>
          <li>• Automatically handles JSON request/response bodies</li>
          <li>• Path parameters and query strings are parsed correctly</li>
        </ul>
      </div>
    </div>
  );
} 