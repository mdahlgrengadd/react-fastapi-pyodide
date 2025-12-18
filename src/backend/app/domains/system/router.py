"""System domain router."""
import asyncio
import json
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.deps import get_current_user
from app.core.runtime import get_environment_info
from app.db.session import DATABASE_URL, ENVIRONMENT

router = APIRouter()


class SSEStream(StreamingResponse):
    """Minimal SSE-friendly response without Starlette helpers."""

    def __init__(self, generator):
        super().__init__(generator, media_type="text/event-stream")
        self.headers["Cache-Control"] = "no-cache"
        self.headers["Connection"] = "keep-alive"


@router.get("/",
            summary="Welcome to Enhanced Bridge Demo",
            tags=["system"],
            operation_id="read_root")
def read_root(current_user: dict = Depends(get_current_user)):
    """Welcome endpoint showcasing dependency injection and persistence info."""

    # Check if we're using persistent storage
    is_persistent = "persist" in DATABASE_URL
    env_info = get_environment_info()

    return {
        "message": f"Welcome {current_user['name']} to Enhanced SQLAlchemy Bridge Demo!",
        "environment": current_user["environment"],
        "persistence": {
            "enabled": is_persistent,
            "database_url": DATABASE_URL,
            "status": "Data survives page reloads!" if is_persistent else "Using in-memory database",
            "note": "Try refreshing the page - your data will still be here!" if is_persistent else "Data will reset when you refresh the page"
        },
        "features": [
            "Direct SQLAlchemy model returns",
            "Automatic JSON serialization",
            "Full dependency injection",
            "Standard FastAPI patterns",
            "Zero code changes needed",
            "Async endpoint support",
            "Persistent storage (survives reloads)" if is_persistent else "In-memory storage (resets on reload)"
        ],
        "endpoints": {
            "users": "/users - Get all users (SQLAlchemy list)",
            "user": "/users/1 - Get single user (SQLAlchemy model)",
            "posts": "/posts - Get all posts (with relationships)",
            "dashboard": "/dashboard - Complex mixed response",
            "async_demo": "/system/async-demo - Async endpoint demonstration",
            "persistence": "/persistence/status - Detailed persistence information",
            "docs": "/docs - Interactive API documentation"
        },
        "runtime_info": env_info
    }


@router.get("/system/info",
            summary="System information",
            description="Get system and runtime information",
            tags=["system"],
            operation_id="get_system_info")
def get_system_info(current_user: dict = Depends(get_current_user)):
    """Get comprehensive system information."""
    env_info = get_environment_info()

    return {
        "system": env_info,
        "user": current_user,
        "database": {
            "url": DATABASE_URL,
            "environment": ENVIRONMENT,
            "persistent": "persist" in DATABASE_URL
        },
        "timestamp": datetime.utcnow()
    }


@router.get("/persistence/status",
            summary="Detailed persistence information",
            description="Get comprehensive information about data persistence",
            tags=["system"],
            operation_id="get_persistence_status")
def get_persistence_status(current_user: dict = Depends(get_current_user)):
    """Get detailed persistence status information."""
    is_persistent = "persist" in DATABASE_URL
    env_info = get_environment_info()

    return {
        "persistence": {
            "enabled": is_persistent,
            "type": "IndexedDB (IDBFS)" if env_info["is_pyodide"] else "File System",
            "database_url": DATABASE_URL,
            "environment": ENVIRONMENT,
            "description": {
                "pyodide-persistent": "Data is stored in browser IndexedDB and survives page reloads",
                "fastapi-production": "Data is stored in production database",
                "fastapi-development": "Data is stored in temporary SQLite file"
            }.get(ENVIRONMENT, "Unknown environment")
        },
        "runtime": env_info,
        "user": current_user,
        "status_check": {
            "timestamp": datetime.utcnow(),
            "message": "Persistence status checked successfully"
        }
    }


@router.get("/system/async-demo",
            summary="Async endpoint demonstration",
            description="Demonstrates async functionality with simulated work",
            tags=["system"],
            operation_id="async_demo")
async def async_demo(current_user: dict = Depends(get_current_user)):
    """Demonstrate async functionality with simulated async work."""
    start_time = datetime.utcnow()

    # Simulate some async work
    steps = []

    steps.append({
        "step": 1,
        "action": "Starting async operation",
        "timestamp": datetime.utcnow(),
        "status": "started"
    })

    # Simulate async database query
    await asyncio.sleep(0.1)  # 100ms delay
    steps.append({
        "step": 2,
        "action": "Simulated database query",
        "timestamp": datetime.utcnow(),
        "status": "completed"
    })

    # Simulate async API call
    await asyncio.sleep(0.15)  # 150ms delay
    steps.append({
        "step": 3,
        "action": "Simulated external API call",
        "timestamp": datetime.utcnow(),
        "status": "completed"
    })

    # Simulate async processing
    await asyncio.sleep(0.05)  # 50ms delay
    steps.append({
        "step": 4,
        "action": "Data processing",
        "timestamp": datetime.utcnow(),
        "status": "completed"
    })

    end_time = datetime.utcnow()
    total_duration = (end_time - start_time).total_seconds()

    return {
        "message": "Async demonstration completed successfully",
        "user": current_user,
        "async_demo": {
            "total_duration_seconds": total_duration,
            "start_time": start_time,
            "end_time": end_time,
            "steps_completed": len(steps),
            "execution_steps": steps
        },
        "environment": get_environment_info(),
        "note": "This endpoint demonstrates async/await functionality in Pyodide"
    }


@router.get("/health-async", operation_id="health_async")
async def health_check_async(current_user: dict = Depends(get_current_user)):
    """Async health check endpoint demonstrating async operations."""
    start_time = datetime.now()

    # Simulate some async work
    await asyncio.sleep(0.1)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    return {
        "status": "healthy",
        "async": True,
        "duration_seconds": duration,
        "timestamp": end_time.isoformat(),
        "environment": ENVIRONMENT,
        "database_url": DATABASE_URL.replace("sqlite:///", "").split("/")[-1] if "sqlite" in DATABASE_URL else "async-capable",
        "user": current_user,
        "message": "Async health check completed successfully"
    }


# ============================================================================
# OLD SIMULATED STREAMING ENDPOINTS REMOVED
# Replaced by TRUE streaming endpoints below (async_monitor_stream, etc.)
# ============================================================================


# ============================================================================
# TRUE STREAMING ENDPOINTS (SSE with real-time chunk delivery)
# ============================================================================

async def system_event_generator(
    total_events: int = 20,
    interval_seconds: float = 1.0,
    ping_interval: int = 10,
):
    """
    System events streaming - REWRITTEN from scratch using WORKING pattern.
    Sends events with proper SSE format that matches async_monitor_stream pattern.
    """
    start_time = datetime.now()
    print(f"🎬 Starting system events stream with {total_events} events")

    # Send initial metadata (matches working pattern)
    metadata = {
        "type": "metadata",
        "total_events": total_events,
        "interval_seconds": interval_seconds,
        "start_time": start_time.isoformat()
    }
    print(f"📤 Yielding metadata")
    yield f"data: {json.dumps(metadata)}\n\n".encode("utf-8")

    # Stream each event (matches working pattern)
    for i in range(1, total_events + 1):
        event_start = datetime.now()

        # Simulate async work
        await asyncio.sleep(interval_seconds)

        event_end = datetime.now()
        event_duration = (event_end - event_start).total_seconds()

        # Send event data (structured like iterations)
        event_data = {
            "type": "event",
            "event_number": i,
            "event_name": "tick",
            "timestamp": event_end.isoformat(),
            "duration_seconds": round(event_duration, 3),
            "message": f"System heartbeat {i}/{total_events}",
            "progress_percent": round((i / total_events) * 100, 1)
        }

        print(f"📤 Yielding event {i}/{total_events}")
        yield f"data: {json.dumps(event_data)}\n\n".encode("utf-8")

    # Send completion summary (matches working pattern)
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()

    summary = {
        "type": "complete",
        "total_events": total_events,
        "total_duration_seconds": round(total_duration, 3),
        "average_event_duration": round(total_duration / total_events, 3),
        "end_time": end_time.isoformat()
    }

    print(f"📤 Yielding summary")
    yield f"data: {json.dumps(summary)}\n\n".encode("utf-8")

    # Signal stream end
    print(f"📤 Yielding close event")
    yield b"event: close\ndata: stream-complete\n\n"
    print(
        f"✅ System events stream complete - yielded {total_events + 3} chunks total")


@router.get(
    "/system/events",
    summary="Server-sent events demo with TRUE streaming",
    description="Streams events in real-time!",
    tags=["system"],
    operation_id="system_events",
)
async def system_events(
    current_user: dict = Depends(get_current_user),
    total_events: int = Query(default=10, ge=1, le=200),
    interval_seconds: float = Query(default=0.75, ge=0.05, le=5.0),
):
    """TRUE streaming endpoint - manually iterated by frontend.

    Returns StreamingResponse with async generator for true streaming.
    """
    generator = system_event_generator(
        total_events=total_events,
        interval_seconds=interval_seconds,
    )
    return SSEStream(generator)


async def async_monitor_stream_generator(
    monitor_duration: int = 10,
    check_interval: float = 0.15,
):
    """
    Real streaming generator for monitoring - sends data as it's generated.
    This is TRUE streaming, not batch-then-display.
    """
    start_time = datetime.now()

    # Send initial metadata
    metadata = {
        "type": "metadata",
        "monitor_duration": monitor_duration,
        "check_interval": check_interval,
        "start_time": start_time.isoformat()
    }
    yield f"data: {json.dumps(metadata)}\n\n".encode("utf-8")

    # Stream monitoring data in real-time
    for i in range(1, monitor_duration + 1):
        check_start = datetime.now()

        # Simulate varying response times for different metrics
        await asyncio.sleep(check_interval * (0.8 + (i % 3) * 0.1))

        check_end = datetime.now()
        response_time = (check_end - check_start).total_seconds()

        # Generate realistic-looking metrics
        base_cpu = 25 + (i * 2) + (i % 7) * 5
        cpu_usage = min(95, max(10, base_cpu + (i % 11) * 3))

        memory_base = 45 + (i * 1.5)
        memory_usage = min(90, max(20, memory_base + (i % 5) * 4))

        # Send this iteration's data immediately
        iteration_data = {
            "type": "iteration",
            "iteration": i,
            "timestamp": check_end.isoformat(),
            "response_time_ms": round(response_time * 1000, 1),
            "metrics": {
                "cpu_usage_percent": round(cpu_usage, 1),
                "memory_usage_percent": round(memory_usage, 1),
                "active_connections": 12 + (i % 8),
                "requests_per_minute": 150 + (i * 5) + (i % 13) * 10,
                "async_tasks_running": 3 + (i % 4)
            },
            "status": "healthy" if cpu_usage < 80 and memory_usage < 85 else "warning"
        }
        yield f"data: {json.dumps(iteration_data)}\n\n".encode("utf-8")

    # Send completion summary
    end_time = datetime.now()
    total_time = (end_time - start_time).total_seconds()
    summary = {
        "type": "complete",
        "total_iterations": monitor_duration,
        "total_time_seconds": round(total_time, 3),
        "end_time": end_time.isoformat()
    }
    yield f"data: {json.dumps(summary)}\n\n".encode("utf-8")

    # Signal stream end
    yield b"event: close\ndata: stream-complete\n\n"


@router.get(
    "/async-monitor-stream",
    summary="Real-time monitoring with TRUE streaming",
    description="Streams monitoring data in real-time as it's generated!",
    tags=["system", "streaming"],
    operation_id="async_monitor_stream",
)
async def async_monitor_stream(
    monitor_duration: int = Query(
        default=10, ge=5, le=30, description="Monitoring duration in iterations"),
    check_interval: float = Query(
        default=0.15, ge=0.05, le=0.5, description="Interval between checks"),
    current_user: dict = Depends(get_current_user)
):
    """TRUE streaming endpoint - manually iterated by frontend for real-time updates.

    Returns StreamingResponse with async generator for true streaming.
    """
    generator = async_monitor_stream_generator(
        monitor_duration=monitor_duration,
        check_interval=check_interval,
    )
    return SSEStream(generator)


async def async_simulation_stream_generator(
    steps: int = 5,
    delay: float = 0.1,
):
    """
    Real streaming generator for simulation - sends data as each step completes.
    """
    start_time = datetime.now()
    print(f"🎬 Starting simulation stream with {steps} steps")

    # Send initial metadata
    metadata = {
        "type": "metadata",
        "total_steps": steps,
        "delay_per_step": delay,
        "start_time": start_time.isoformat()
    }
    print(f"📤 Yielding metadata")
    yield f"data: {json.dumps(metadata)}\n\n".encode("utf-8")

    # Stream each simulation step in real-time
    for step in range(1, steps + 1):
        step_start = datetime.now()

        # Simulate async work with varying delays
        step_delay = delay * (0.5 + step * 0.1)
        await asyncio.sleep(step_delay)

        step_end = datetime.now()
        step_duration = (step_end - step_start).total_seconds()

        # Send this step's result immediately
        step_data = {
            "type": "step",
            "step": step,
            "status": "completed",
            "duration_seconds": round(step_duration, 3),
            "simulated_work": f"Processing batch {step} of {steps}",
            "timestamp": step_end.isoformat(),
            "progress_percent": round((step / steps) * 100, 1)
        }
        print(f"📤 Yielding step {step}/{steps}")
        yield f"data: {json.dumps(step_data)}\n\n".encode("utf-8")

    # Send completion summary
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    summary = {
        "type": "complete",
        "total_steps": steps,
        "total_duration_seconds": round(total_duration, 3),
        "average_step_duration": round(total_duration / steps, 3),
        "end_time": end_time.isoformat()
    }
    print(f"📤 Yielding summary")
    yield f"data: {json.dumps(summary)}\n\n".encode("utf-8")

    # Signal stream end
    print(f"📤 Yielding close event")
    yield b"event: close\ndata: stream-complete\n\n"
    print(f"✅ Simulation stream complete - yielded {steps + 3} chunks total")


@router.get(
    "/async-simulation-stream",
    summary="Async simulation with TRUE streaming",
    description="Streams simulation results in real-time as each step completes!",
    tags=["system", "streaming"],
    operation_id="async_simulation_stream",
)
async def async_simulation_stream(
    steps: int = Query(default=5, ge=1, le=20,
                       description="Number of simulation steps"),
    delay: float = Query(default=0.1, ge=0.01, le=1.0,
                         description="Delay between steps in seconds"),
    current_user: dict = Depends(get_current_user)
):
    """TRUE streaming endpoint - manually iterated by frontend for real-time updates.

    Returns StreamingResponse with async generator for true streaming.
    """
    generator = async_simulation_stream_generator(
        steps=steps,
        delay=delay,
    )
    return SSEStream(generator)
