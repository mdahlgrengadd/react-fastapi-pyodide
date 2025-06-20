import { Link } from 'react-router-dom';
import { useAPIQuery } from 'react-router-fastapi';

export const SystemPage: React.FC = () => {
  const { data: systemInfo, isLoading, error, refetch } = useAPIQuery<{
    app_name: string;
    version: string;
    description: string;
    python_version: string;
    environment: string;
  }>('system-info', '/api/v1/system/info');

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto p-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">System Information</h1>
            <p className="text-gray-600">Monitor system status and configuration</p>
          </div>
          <Link
            to="/"
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            ← Home
          </Link>
        </div>

        {/* System Status Card */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">System Status</h2>
            <button
              onClick={() => refetch()}
              disabled={isLoading}
              className={`px-3 py-1 rounded text-sm transition-colors ${
                isLoading
                  ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                  : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
              }`}
            >
              {isLoading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>

          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
              <span className="ml-3 text-gray-600">Loading system information...</span>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-red-500 rounded-full mr-3"></div>
                <p className="text-red-800 font-medium">Failed to load system information</p>
              </div>
              <p className="text-red-600 text-sm mt-2">{error instanceof Error ? error.message : 'Unknown error'}</p>
            </div>
          )}

          {systemInfo && (
            <div className="grid md:grid-cols-2 gap-6">
              <InfoCard
                title="Application"
                items={[
                  { label: 'Name', value: systemInfo.app_name },
                  { label: 'Version', value: systemInfo.version },
                  { label: 'Environment', value: systemInfo.environment || 'Unknown' },
                ]}
                icon="🚀"
              />
              <InfoCard
                title="Runtime"
                items={[
                  { label: 'Python Version', value: systemInfo.python_version || 'Unknown' },
                  { label: 'Platform', value: 'Pyodide (WebAssembly)' },
                  { label: 'Status', value: 'Running' },
                ]}
                icon="⚙️"
              />
            </div>
          )}
        </div>

        {/* API Information */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-semibold mb-4">🔗 API Integration</h2>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-blue-50 rounded-lg p-4">
              <h3 className="font-semibold text-blue-900 mb-2">Fetch Interception</h3>
              <p className="text-blue-700 text-sm mb-3">
                All API calls are automatically intercepted and routed through the Pyodide bridge.
              </p>
              <code className="text-xs bg-blue-200 px-2 py-1 rounded">
                fetch('/api/v1/system/info') → Pyodide Bridge
              </code>
            </div>
            <div className="bg-green-50 rounded-lg p-4">
              <h3 className="font-semibold text-green-900 mb-2">React Query Caching</h3>
              <p className="text-green-700 text-sm mb-3">
                API responses are cached and can be refreshed on demand.
              </p>
              <code className="text-xs bg-green-200 px-2 py-1 rounded">
                useAPIQuery('system-info', '/api/v1/system/info')
              </code>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

interface InfoCardProps {
  title: string;
  items: { label: string; value: string }[];
  icon: string;
}

const InfoCard: React.FC<InfoCardProps> = ({ title, items, icon }) => {
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <div className="flex items-center mb-3">
        <span className="text-xl mr-2">{icon}</span>
        <h3 className="font-semibold text-gray-900">{title}</h3>
      </div>
      <div className="space-y-2">
        {items.map((item, index) => (
          <div key={index} className="flex justify-between">
            <span className="text-gray-600 text-sm">{item.label}:</span>
            <span className="text-gray-900 text-sm font-medium">{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}; 