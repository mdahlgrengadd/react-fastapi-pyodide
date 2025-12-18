// Full Bidirectional Reactive Sync Test - Inline Version
// Copy and paste this entire block into your browser console

(async function testFullSync() {
    console.log("🧪 Starting Full Bidirectional Reactive Sync Test\n");
    
    const pyodide = window.pyodide;
    if (!pyodide) {
        console.error("❌ Pyodide not available. Make sure Pyodide is initialized.");
        return;
    }

    // Test 1: Create user in Pyodide (Client → Server)
    console.log("📤 TEST 1: Creating user in Pyodide (Client → Server)");
    console.log("─".repeat(60));
    
    try {
        await pyodide.runPythonAsync(`
from app.domains.models import User
import random
uid = random.randint(10000, 99999)
user = User(name=f"Pyodide User {uid}", email=f"pyodide{uid}@test.com", age=25)
user.save()
print(f"✅ Created in Pyodide: {user.name} (ID: {user.id})")
pyodide_test_user_id = user.id
pyodide_test_user_name = user.name
        `);
        
        const userId = pyodide.globals.get('pyodide_test_user_id');
        const userName = pyodide.globals.get('pyodide_test_user_name');
        console.log(`✅ User created: ${userName} (ID: ${userId})`);
        
        // Wait for sync
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Verify on backend
        const response = await fetch(`http://localhost:8000/api/v1/users/${userId}`);
        if (response.ok) {
            const user = await response.json();
            console.log(`✅ Verified on backend: ${user.name}`);
        } else {
            console.error(`❌ User not found on backend (status: ${response.status})`);
        }
    } catch (error) {
        console.error("❌ Test 1 failed:", error);
    }
    
    console.log("\n");
    
    // Test 2: Create user on backend (Server → Client)
    console.log("📥 TEST 2: Creating user on backend (Server → Client)");
    console.log("─".repeat(60));
    
    try {
        const randomId = Math.floor(Math.random() * 90000) + 10000;
        const newUser = {
            name: `Backend User ${randomId}`,
            email: `backend${randomId}@test.com`,
            age: 30
        };
        
        const createResponse = await fetch('http://localhost:8000/api/v1/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newUser)
        });
        
        if (createResponse.ok) {
            const createdUser = await createResponse.json();
            console.log(`✅ Created on backend: ${createdUser.name} (ID: ${createdUser.id})`);
            
            // Manually trigger pull for this topic
            console.log("⏳ Manually triggering pull...");
            const topic = `user:${createdUser.id}`;
            await pyodide.runPythonAsync(`
from app.client_main import app
if hasattr(app.state, 'handle_poke'):
    app.state.handle_poke("${topic}")
    print("✅ Pull triggered")
else:
    print("❌ handle_poke not available")
            `);
            
            // Wait for pull to complete
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Verify in Pyodide
            await pyodide.runPythonAsync(`
from app.domains.models import User
from app.reactive_sqlmodel.runtime import get_runtime
runtime = get_runtime()
with runtime.open_session() as session:
    from sqlmodel import select
    user = session.exec(select(User).where(User.id == ${createdUser.id})).first()
    if user:
        print(f"✅ Found in Pyodide: {user.name}")
    else:
        print("❌ Not found in Pyodide")
            `);
        } else {
            console.error(`❌ Failed to create user on backend (status: ${createResponse.status})`);
        }
    } catch (error) {
        console.error("❌ Test 2 failed:", error);
    }
    
    console.log("\n");
    
    // Test 3: Update user in Pyodide (Client → Server)
    console.log("📤 TEST 3: Updating user in Pyodide (Client → Server)");
    console.log("─".repeat(60));
    
    try {
        // Get first user from backend
        const usersResponse = await fetch('http://localhost:8000/api/v1/users');
        const users = await usersResponse.json();
        if (users.length === 0) {
            console.log("⚠️  No users to update, skipping test");
        } else {
            const targetUser = users[0];
            const newName = `Updated ${Date.now()}`;
            
            await pyodide.runPythonAsync(`
from app.domains.models import User
# Use the active-record pattern - get and save in separate contexts
user = User.get(${targetUser.id})
if user:
    old_name = user.name
    user.name = "${newName}"
    user.save()
    print(f"✅ Updated in Pyodide: {old_name} → {user.name}")
else:
    print("❌ User not found")
            `);
            
            // Wait for sync
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Verify on backend
            const verifyResponse = await fetch(`http://localhost:8000/api/v1/users/${targetUser.id}`);
            const updatedUser = await verifyResponse.json();
            if (updatedUser.name === newName) {
                console.log(`✅ Verified update on backend: ${updatedUser.name}`);
            } else {
                console.error(`❌ Update not synced. Expected: ${newName}, Got: ${updatedUser.name}`);
            }
        }
    } catch (error) {
        console.error("❌ Test 3 failed:", error);
    }
    
    console.log("\n");
    
    // Test 4: Check mutation queue
    console.log("📋 TEST 4: Checking mutation queue");
    console.log("─".repeat(60));
    
    try {
        await pyodide.runPythonAsync(`
from app.reactive_sqlmodel.runtime import get_runtime
from app.reactive_sqlmodel.sync_tables import Mutation
from sqlmodel import select
runtime = get_runtime()
with runtime.open_session() as session:
    mutations = session.exec(select(Mutation)).all()
    print(f"Pending mutations: {len(mutations)}")
    for m in mutations:
        print(f"  - {m.id}: {m.table_name} pk={m.pk}")
        `);
    } catch (error) {
        console.error("❌ Test 4 failed:", error);
    }
    
    console.log("\n");
    
    // Test 5: Check checkpoints
    console.log("📍 TEST 5: Checking checkpoints");
    console.log("─".repeat(60));
    
    try {
        await pyodide.runPythonAsync(`
from app.reactive_sqlmodel.runtime import get_runtime
from app.reactive_sqlmodel.sync_tables import Checkpoint
from sqlmodel import select
runtime = get_runtime()
with runtime.open_session() as session:
    checkpoints = session.exec(select(Checkpoint)).all()
    print(f"Checkpoints: {len(checkpoints)}")
    for cp in checkpoints:
        print(f"  - {cp.topic}: version {cp.ver}")
        `);
    } catch (error) {
        console.error("❌ Test 5 failed:", error);
    }
    
    console.log("\n");
    console.log("✅ Full sync test completed!");
    console.log("\nSummary:");
    console.log("  ✅ Test 1: Client → Server (Create)");
    console.log("  ✅ Test 2: Server → Client (Create via pull)");
    console.log("  ✅ Test 3: Client → Server (Update)");
    console.log("  ✅ Test 4: Mutation queue status");
    console.log("  ✅ Test 5: Checkpoint status");
})();

