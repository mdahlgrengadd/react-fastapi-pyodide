import { Link } from 'react-router-dom';
import { useAPIQuery } from 'react-router-fastapi';

export const DashboardPage: React.FC = () => {
  const { data: dashboardData, isLoading, error } = useAPIQuery<{
    total_users: number;
    total_posts: number;
    active_sessions: number;
    system_status: string;
  }>('dashboard', '/api/v1/dashboard');

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto p-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Dashboard</h1>
            <p className="text-gray-600">Overview of system statistics and metrics</p>
          </div>
          <Link
            to="/"
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            ← Home
          </Link>
        </div>

        {/* Stats Cards */}
        {isLoading && (
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-white rounded-lg shadow-lg p-6">
                <div className="animate-pulse">
                  <div className="h-4 bg-gray-200 rounded w-3/4 mb-3"></div>
                  <div className="h-8 bg-gray-200 rounded w-1/2"></div>
                </div>
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-800 font-medium">Failed to load dashboard data</p>
              <p className="text-red-600 text-sm mt-1">{error instanceof Error ? error.message : 'Unknown error'}</p>
            </div>
          </div>
        )}

        {dashboardData && (
          <>
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <StatCard
                title="Total Users"
                value={dashboardData.total_users}
                icon="👥"
                color="blue"
                change="+12%"
              />
              <StatCard
                title="Total Posts"
                value={dashboardData.total_posts}
                icon="📝"
                color="green"
                change="+5%"
              />
              <StatCard
                title="Active Sessions"
                value={dashboardData.active_sessions}
                icon="🔗"
                color="purple"
                change="+8%"
              />
              <StatCard
                title="System Status"
                value={dashboardData.system_status}
                icon="⚡"
                color="orange"
                isText={true}
              />
            </div>

            {/* Charts and Additional Info */}
            <div className="grid lg:grid-cols-2 gap-8">
              <div className="bg-white rounded-lg shadow-lg p-6">
                <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
                <div className="grid grid-cols-2 gap-4">
                  <ActionButton
                    to="/users"
                    title="Manage Users"
                    description="View and edit user accounts"
                    icon="👥"
                  />
                  <ActionButton
                    to="/posts"
                    title="Manage Posts"
                    description="Create and edit blog posts"
                    icon="📝"
                  />
                  <ActionButton
                    to="/system"
                    title="System Info"
                    description="Check system health"
                    icon="⚙️"
                  />
                  <div className="p-4 border-2 border-dashed border-gray-300 rounded-lg text-center text-gray-500">
                    <span className="text-2xl mb-2 block">➕</span>
                    <span className="text-sm">More Actions</span>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow-lg p-6">
                <h2 className="text-xl font-semibold mb-4">Recent Activity</h2>
                <div className="space-y-4">
                  <ActivityItem
                    action="User registration"
                    user="john@example.com"
                    time="2 minutes ago"
                    type="user"
                  />
                  <ActivityItem
                    action="New post created"
                    user="admin@example.com"
                    time="15 minutes ago"
                    type="post"
                  />
                  <ActivityItem
                    action="System backup completed"
                    user="system"
                    time="1 hour ago"
                    type="system"
                  />
                  <ActivityItem
                    action="User login"
                    user="jane@example.com"
                    time="2 hours ago"
                    type="user"
                  />
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

interface StatCardProps {
  title: string;
  value: number | string;
  icon: string;
  color: 'blue' | 'green' | 'purple' | 'orange';
  change?: string;
  isText?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, color, change, isText = false }) => {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    orange: 'bg-orange-50 text-orange-600',
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <span className="text-xl">{icon}</span>
        </div>
        {change && (
          <span className="text-green-600 text-sm font-medium">{change}</span>
        )}
      </div>
      <div>
        <p className="text-gray-600 text-sm mb-1">{title}</p>
        <p className="text-2xl font-bold text-gray-900">
          {isText ? String(value) : (typeof value === 'number' ? value.toLocaleString() : String(value || '0'))}
        </p>
      </div>
    </div>
  );
};

interface ActionButtonProps {
  to: string;
  title: string;
  description: string;
  icon: string;
}

const ActionButton: React.FC<ActionButtonProps> = ({ to, title, description, icon }) => {
  return (
    <Link
      to={to}
      className="p-4 border-2 border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors group"
    >
      <div className="text-center">
        <span className="text-2xl mb-2 block group-hover:scale-110 transition-transform">{icon}</span>
        <h3 className="font-medium text-gray-900 mb-1">{title}</h3>
        <p className="text-xs text-gray-600">{description}</p>
      </div>
    </Link>
  );
};

interface ActivityItemProps {
  action: string;
  user: string;
  time: string;
  type: 'user' | 'post' | 'system';
}

const ActivityItem: React.FC<ActivityItemProps> = ({ action, user, time, type }) => {
  const typeIcons = {
    user: '👤',
    post: '📄',
    system: '⚙️',
  };

  const typeColors = {
    user: 'bg-blue-100 text-blue-800',
    post: 'bg-green-100 text-green-800',
    system: 'bg-orange-100 text-orange-800',
  };

  return (
    <div className="flex items-center p-3 bg-gray-50 rounded-lg">
      <div className={`p-2 rounded-full ${typeColors[type]} mr-3`}>
        <span className="text-sm">{typeIcons[type]}</span>
      </div>
      <div className="flex-1">
        <p className="text-sm font-medium text-gray-900">{action}</p>
        <p className="text-xs text-gray-600">{user} • {time}</p>
      </div>
    </div>
  );
}; 