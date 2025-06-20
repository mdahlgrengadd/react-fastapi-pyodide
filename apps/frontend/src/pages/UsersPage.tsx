// Auto-generated page component using generated TypeScript client
import React from 'react';
import { Link, useParams } from 'react-router-dom';
import { getUsers, getUser } from '../client';
import { useQuery } from 'react-query';

export const UsersPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  if (id) {
    return <UsersDetail id={id} />;
  }
  return <UsersList />;
};

const UsersList: React.FC = () => {
  const {
    data: users,
    isLoading,
    error
  } = useQuery(['users'], () => getUsers());

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto p-8">        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Users Management</h1>
            <p className="text-gray-600">Manage users data and entries</p>
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
              <p className="text-red-800 font-medium">Failed to load users</p>
              <p className="text-red-600 text-sm mt-1">{error instanceof Error ? error.message : 'Unknown error'}</p>
            </div>
          </div>
        ) : null}

        {users && Array.isArray(users) && users.length > 0 ? (
          <div className="bg-white rounded-lg shadow-lg overflow-hidden">
            <div className="p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Users</h2>
              <div className="space-y-4">
                {users.map((item: any, index: number) => (
                  <div key={item.id || index} className="border rounded-lg p-4 hover:bg-gray-50">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-medium text-gray-900">
                          {item.name || item.title || item.email || `Users ${item.id || index + 1}`}
                        </h3>
                        {item.description && (
                          <p className="text-gray-600 text-sm mt-1">{item.description}</p>
                        )}
                      </div>
                      {item.id && (
                        <Link
                          to={`/users/${item.id}`}
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

const UsersDetail: React.FC<{ id: string }> = ({ id }) => {
  const {
    data: users,
    isLoading,
    error  } = useQuery(['users', id], () => getUser({ userId: parseInt(id) }));

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto p-8">        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Users Details</h1>
            <p className="text-gray-600">View detailed information for this users</p>
          </div>
          <div className="space-x-2">
            <Link
              to="/users"
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              ← Back to Users
            </Link>
            <Link
              to="/"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Home
            </Link>
          </div>
        </div>        {isLoading ? (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="animate-pulse space-y-4">
              <div className="h-6 bg-gray-200 rounded w-1/3"></div>
              <div className="h-4 bg-gray-200 rounded w-2/3"></div>
              <div className="h-4 bg-gray-200 rounded w-1/2"></div>
            </div>
          </div>
        ) : null}

        {error ? (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-800 font-medium">Failed to load users details</p>
              <p className="text-red-600 text-sm mt-1">{error instanceof Error ? error.message : 'Unknown error'}</p>
            </div>
          </div>
        ) : null}

        {users ? (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Users Information</h2>
            <div className="grid md:grid-cols-2 gap-6">
              {Object.entries(users).map(([key, value]) => (
                <div key={key} className="border-b border-gray-200 pb-2">
                  <dt className="text-sm font-medium text-gray-500 capitalize">
                    {key.replace('_', ' ')}
                  </dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                  </dd>
                </div>
              ))}            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};
