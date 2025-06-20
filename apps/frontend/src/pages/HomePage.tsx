import { Link } from 'react-router-dom';
import { useAPIQuery } from 'react-router-fastapi';

export const HomePage: React.FC = () => {
  // Test API call to verify the integration works
  const { data: systemInfo, isLoading, error } = useAPIQuery<{
    app_name: string;
    version: string;
    description: string;
  }>('system-info', '/api/v1/system/info');

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto p-8">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            React × FastAPI × Pyodide
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Seamless integration with URL-based routing and API endpoints
          </p>
          
          {/* API Status Indicator */}
          <div className="inline-flex items-center px-4 py-2 rounded-full bg-green-100 text-green-800 mb-8">
            <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
            <span className="font-medium">
              {isLoading ? 'Connecting to API...' : 
               error ? 'API Error' : 
               systemInfo ? `${systemInfo.app_name} v${systemInfo.version} - Active` : 
               'API Status Unknown'}
            </span>
          </div>
        </div>

        {/* Navigation Cards */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          <NavigationCard
            to="/dashboard"
            title="📊 Dashboard"
            description="View dashboard statistics and charts"
            color="blue"
          />
          <NavigationCard
            to="/system"
            title="⚙️ System Info"
            description="Check system status and configuration"
            color="green"
          />
          <NavigationCard
            to="/users"
            title="👥 Users"
            description="Manage users and permissions"
            color="purple"
          />
          <NavigationCard
            to="/posts"
            title="📝 Posts"
            description="Browse and manage blog posts"
            color="orange"
          />
        </div>

        {/* API Demo Section */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-semibold mb-4">🚀 Live API Demo</h2>
          <p className="text-gray-600 mb-4">
            This data is fetched directly from the FastAPI backend running in Pyodide:
          </p>
          
          {isLoading && (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
              <span className="ml-2 text-gray-600">Loading system info...</span>
            </div>
          )}
          
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-800">Error loading system info: {error.message}</p>
            </div>
          )}
          
          {systemInfo && (
            <div className="bg-gray-50 rounded-lg p-4">
              <pre className="text-sm text-gray-800 font-mono">
                {JSON.stringify(systemInfo, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Features Section */}
        <div className="mt-12 grid md:grid-cols-2 gap-8">
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-xl font-semibold mb-4">✨ Features</h3>
            <ul className="space-y-2 text-gray-600">
              <li>• URL-based routing with React Router</li>
              <li>• Automatic API endpoint discovery</li>
              <li>• Fetch interception for seamless API calls</li>
              <li>• TypeScript support throughout</li>
              <li>• React Query integration for caching</li>
              <li>• Python FastAPI backend in browser</li>
            </ul>
          </div>

          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-xl font-semibold mb-4">🔧 How It Works</h3>
            <ol className="space-y-2 text-gray-600 list-decimal list-inside">
              <li>Pyodide loads Python FastAPI backend</li>
              <li>FetchInterceptor routes API calls to Pyodide</li>
              <li>FastAPIRouter handles URL routing</li>
              <li>React Query manages API state</li>
              <li>Components use standard fetch/hooks</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
};

interface NavigationCardProps {
  to: string;
  title: string;
  description: string;
  color: 'blue' | 'green' | 'purple' | 'orange';
}

const NavigationCard: React.FC<NavigationCardProps> = ({ to, title, description, color }) => {
  const colorClasses = {
    blue: 'bg-blue-50 hover:bg-blue-100 border-blue-200 text-blue-800',
    green: 'bg-green-50 hover:bg-green-100 border-green-200 text-green-800',
    purple: 'bg-purple-50 hover:bg-purple-100 border-purple-200 text-purple-800',
    orange: 'bg-orange-50 hover:bg-orange-100 border-orange-200 text-orange-800',
  };

  return (
    <Link
      to={to}
      className={`block p-6 rounded-lg border-2 transition-colors ${colorClasses[color]}`}
    >
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-sm opacity-75">{description}</p>
    </Link>
  );
}; 