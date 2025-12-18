/**
 * Reactive Sync Test Component
 *
 * This component provides UI for testing the reactive SQLModel sync functionality:
 * - Create/update/delete users from the browser
 * - See real-time sync with server
 * - Monitor SSE poke notifications
 * - View sync queue status
 */

import React, { useState, useEffect } from 'react';
import { usePyodide } from './Context';

export const ReactiveSyncTest: React.FC = () => {
  const { pyodideEngine } = usePyodide();
  const [output, setOutput] = useState<string>('');
  const [users, setUsers] = useState<any[]>([]);
  const [syncStatus, setSyncStatus] = useState<string>('Not connected');
  const [subscribedTopics, setSubscribedTopics] = useState<string[]>([]);

  useEffect(() => {
    // Listen for reactive sync events
    const handleSync = (event: any) => {
      const { topic } = event.detail;
      addOutput(`🔄 Sync event: ${topic}`);
      refreshUsers();
    };

    window.addEventListener('reactive-sync', handleSync);
    return () => window.removeEventListener('reactive-sync', handleSync);
  }, []);

  const addOutput = (message: string) => {
    setOutput((prev) => `${new Date().toLocaleTimeString()} - ${message}\n${prev}`);
  };

  const runPython = async (code: string): Promise<any> => {
    if (!pyodideEngine?.isReady()) {
      addOutput('❌ Pyodide not ready');
      return null;
    }

    try {
      const result = await pyodideEngine.getPyodide()?.runPythonAsync(code);
      return result;
    } catch (error: any) {
      addOutput(`❌ Error: ${error.message}`);
      return null;
    }
  };

  const refreshUsers = async () => {
    const code = `
from app.domains.models import User
import json

users = User.all()
json.dumps([{
    'id': u.id,
    'name': u.name,
    'email': u.email,
    'age': u.age
} for u in users])
    `;

    const result = await runPython(code);
    if (result) {
      const usersData = JSON.parse(result);
      setUsers(usersData);
      addOutput(`✅ Loaded ${usersData.length} users`);
    }
  };

  const createUser = async () => {
    const timestamp = Date.now();
    const code = `
from app.domains.models import User

user = User(
    name="Test User ${timestamp}",
    email="test${timestamp}@example.com",
    age=25
)
user.save()
print(f"Created user: {user.name} (id={user.id})")
"User created successfully"
    `;

    const result = await runPython(code);
    if (result) {
      addOutput(`✅ ${result}`);
      await refreshUsers();
    }
  };

  const deleteUser = async (userId: number) => {
    const code = `
from app.domains.models import User

user = User.get(${userId})
if user:
    name = user.name
    user.delete()
    print(f"Deleted user: {name}")
    "User deleted successfully"
else:
    "User not found"
    `;

    const result = await runPython(code);
    if (result) {
      addOutput(`✅ ${result}`);
      await refreshUsers();
    }
  };

  const subscribeTopic = async (topic: string) => {
    if (pyodideEngine) {
      pyodideEngine.subscribeToTopics([topic]);
      setSubscribedTopics([...subscribedTopics, topic]);
      addOutput(`✅ Subscribed to topic: ${topic}`);
    }
  };

  const checkSyncStatus = async () => {
    const code = `
from app.client_main import app

# Check if handle_poke exists
has_handler = hasattr(app.state, 'handle_poke')

# Check if REACTIVE_TRANSPORT exists
import js
has_transport = hasattr(js, 'REACTIVE_TRANSPORT')

# Get sync manager status
from app.reactive_sqlmodel import get_runtime
try:
    runtime = get_runtime()
    has_sync = runtime.sync is not None
except:
    has_sync = False

import json
json.dumps({
    'has_handler': has_handler,
    'has_transport': has_transport,
    'has_sync': has_sync
})
    `;

    const result = await runPython(code);
    if (result) {
      const status = JSON.parse(result);
      const statusMessage = [
        status.has_handler ? '✅ Poke handler' : '❌ No poke handler',
        status.has_transport ? '✅ Transport' : '❌ No transport',
        status.has_sync ? '✅ ClientSync' : '❌ No ClientSync'
      ].join(' | ');
      setSyncStatus(statusMessage);
      addOutput(`Status: ${statusMessage}`);
    }
  };

  const testPushPull = async () => {
    addOutput('🧪 Testing push/pull cycle...');

    const code = `
from app.reactive_sqlmodel import get_runtime

runtime = get_runtime()
if runtime.sync:
    # Create a test user
    from app.domains.models import User
    user = User(name="Push Test", email="push@test.com", age=30)
    user.save()

    # This triggers:
    # 1. Mutation queued
    # 2. Push to server
    # 3. Server writes to ChangeLog
    # 4. Server broadcasts poke

    print(f"✅ Created user {user.id}, sync triggered")
    "Push completed - check server logs for ChangeLog entry"
else:
    "❌ ClientSync not initialized"
    `;

    const result = await runPython(code);
    if (result) {
      addOutput(result);
    }
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h2>🔄 Reactive Sync Test Console</h2>

      <div style={{ marginBottom: '20px' }}>
        <h3>Status</h3>
        <div style={{ padding: '10px', background: '#f0f0f0', borderRadius: '4px' }}>
          {syncStatus}
        </div>
        <button onClick={checkSyncStatus} style={{ marginTop: '10px' }}>
          Check Status
        </button>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <h3>Actions</h3>
        <button onClick={createUser} style={{ marginRight: '10px' }}>
          Create User
        </button>
        <button onClick={refreshUsers} style={{ marginRight: '10px' }}>
          Refresh Users
        </button>
        <button onClick={testPushPull} style={{ marginRight: '10px' }}>
          Test Push/Pull
        </button>
        <button onClick={() => subscribeTopic('user:*')}>
          Subscribe to user:*
        </button>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <h3>Users ({users.length})</h3>
        <div style={{ maxHeight: '200px', overflow: 'auto', border: '1px solid #ccc', padding: '10px' }}>
          {users.map((user) => (
            <div key={user.id} style={{ marginBottom: '5px', padding: '5px', background: '#f9f9f9' }}>
              <strong>{user.name}</strong> ({user.email}) - Age: {user.age}
              <button
                onClick={() => deleteUser(user.id)}
                style={{ marginLeft: '10px', fontSize: '12px' }}
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3>Output Log</h3>
        <textarea
          value={output}
          readOnly
          style={{
            width: '100%',
            height: '300px',
            fontFamily: 'monospace',
            fontSize: '12px',
            padding: '10px',
            background: '#1e1e1e',
            color: '#d4d4d4',
            border: '1px solid #444',
          }}
        />
        <button onClick={() => setOutput('')}>Clear Log</button>
      </div>

      <div style={{ marginTop: '20px', fontSize: '12px', color: '#666' }}>
        <strong>Subscribed Topics:</strong> {subscribedTopics.join(', ') || 'None'}
      </div>
    </div>
  );
};
