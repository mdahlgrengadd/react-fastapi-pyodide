import './App.css';

import { BridgeRouter } from 'pyodide-bridge-ts';
import { Routes, Route } from 'react-router-dom';

// Auto-generated page imports
import { 
  AnalyticsPage,
  AsyncPage,
  DashboardPage,
  DashboardsPage,
  HealthPage,
  LivePage,
  PersistencePage,
  PostsPage,
  StreamPage,
  SystemPage,
  UsersPage
} from './pages';

function App() {
  return (
    <BridgeRouter
      packages={["fastapi", "pydantic", "sqlalchemy", "httpx"]}
      debug={true}
      showDevtools={process.env.NODE_ENV === 'development'}
    >
      <Routes>
        <Route path="/" element={<DashboardPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/async" element={<AsyncPage />} />
          <Route path="/dashboards" element={<DashboardsPage />} />
          <Route path="/health" element={<HealthPage />} />
          <Route path="/live" element={<LivePage />} />
          <Route path="/persistence" element={<PersistencePage />} />
          <Route path="/posts" element={<PostsPage />} />
          <Route path="/posts/:id" element={<PostsPage />} />
          <Route path="/stream" element={<StreamPage />} />
          <Route path="/system" element={<SystemPage />} />
          <Route path="/users" element={<UsersPage />} />
          <Route path="/users/:id" element={<UsersPage />} />
      </Routes>
    </BridgeRouter>
  );
}

export default App;
