// Auto-generated page component using generated TypeScript client
import React from 'react';
import { Link } from 'react-router-dom';
import { healthCheckAsync } from '../client';
import { useQuery } from 'react-query';

export const HealthPage: React.FC = () => {
  return <HealthList />;
};

const HealthList: React.FC = () => {
  const {
    data: health,
    isLoading,
    error
  } = useQuery(['health'], () => healthCheckAsync());

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto p-8">        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Health Management</h1>
            <p className="text-gray-600">Manage health data and entries</p>
          </div>
          <Link
            to="/"
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            ← Home
          </Link>
        </div>        {isLoading ? (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="animate-pulse space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-4 bg-gray-200 rounded w-full"></div>
              ))}
            </div>
          </div>
        ) : null}

        {error ? (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-800 font-medium">Failed to load health</p>
              <p className="text-red-600 text-sm mt-1">{error instanceof Error ? error.message : 'Unknown error'}</p>
            </div>
          </div>
        ) : null}

        {health && Array.isArray(health) && health.length > 0 ? (
          <div className="bg-white rounded-lg shadow-lg overflow-hidden">
            <div className="p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Health</h2>
              <div className="space-y-4">
                {health.map((item: any, index: number) => (
                  <div key={item.id || index} className="border rounded-lg p-4 hover:bg-gray-50">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-medium text-gray-900">
                          {item.name || item.title || item.email || `Health ${item.id || index + 1}`}
                        </h3>
                        {item.description && (
                          <p className="text-gray-600 text-sm mt-1">{item.description}</p>
                        )}
                      </div>
                      {item.id && (
                        <Link
                          to={`/health/${item.id}`}
                          className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                        >
                          View Details
                        </Link>
                      )}
                    </div>                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};


