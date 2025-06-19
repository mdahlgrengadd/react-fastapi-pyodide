"""System domain router."""
import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.core.runtime import get_environment_info
from app.db.session import DATABASE_URL, ENVIRONMENT

router = APIRouter()


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


@router.get("/health-async")
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


@router.get("/async-simulation")
async def async_simulation(
    steps: int = Query(default=5, ge=1, le=20,
                       description="Number of simulation steps"),
    delay: float = Query(default=0.1, ge=0.01, le=1.0,
                         description="Delay between steps in seconds"),
    current_user: dict = Depends(get_current_user)
):
    """Simulate async processing with multiple steps to demonstrate real async behavior."""
    start_time = datetime.now()
    results = []

    for step in range(1, steps + 1):
        step_start = datetime.now()

        # Simulate async work with varying delays
        step_delay = delay * (0.5 + step * 0.1)  # Variable delay per step
        await asyncio.sleep(step_delay)

        step_end = datetime.now()
        step_duration = (step_end - step_start).total_seconds()

        results.append({
            "step": step,
            "status": "completed",
            "duration_seconds": round(step_duration, 3),
            "simulated_work": f"Processing batch {step} of {steps}",
            "timestamp": step_end.isoformat()
        })

    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()

    return {
        "message": f"Async simulation completed with {steps} steps",
        "user": current_user,
        "simulation": {
            "total_steps": steps,
            "delay_per_step": delay,
            "results": results,
            "summary": {
                "total_duration_seconds": round(total_duration, 3),
                "average_step_duration": round(total_duration / steps, 3),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
        },
        "environment": ENVIRONMENT,
        "note": "This demonstrates sequential async operations with variable timing"
    }


@router.get("/async-data-stream")
async def async_data_stream(
    batch_size: int = Query(default=3, ge=1, le=10,
                            description="Number of items per batch"),
    batches: int = Query(default=4, ge=1, le=8,
                         description="Number of batches to process"),
    processing_delay: float = Query(
        default=0.08, ge=0.01, le=0.5, description="Processing delay per batch"),
    current_user: dict = Depends(get_current_user)
):
    """Simulate async data streaming with batch processing."""

    async def process_data_batch(batch_num: int, items: int) -> dict:
        """Simulate processing a batch of data asynchronously."""
        start_time = datetime.now()

        # Simulate variable processing time based on batch complexity
        complexity_factor = 1 + (batch_num * 0.2)
        actual_delay = processing_delay * complexity_factor
        await asyncio.sleep(actual_delay)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Simulate some processed data
        processed_items = []
        for i in range(items):
            processed_items.append({
                "item_id": f"batch_{batch_num}_item_{i+1}",
                "value": round(42.5 + (batch_num * 10) + (i * 2.3), 2),
                "status": "processed",
                "metadata": {
                    "batch": batch_num,
                    "position": i + 1,
                    "complexity": round(complexity_factor, 2)
                }
            })

        return {
            "batch_number": batch_num,
            "items_processed": items,
            "processing_time_seconds": round(duration, 3),
            "complexity_factor": round(complexity_factor, 2),
            "data": processed_items,
            "timestamp": end_time.isoformat()
        }

    start_time = datetime.now()

    # Create async tasks for all batches
    tasks = []
    for batch_num in range(1, batches + 1):
        task = asyncio.create_task(
            process_data_batch(batch_num, batch_size),
            name=f"batch_{batch_num}"
        )
        tasks.append(task)

    # Process batches concurrently
    batch_results = await asyncio.gather(*tasks, return_exceptions=True)

    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()

    # Calculate statistics
    successful_batches = [
        r for r in batch_results if not isinstance(r, Exception)]
    total_items = sum(batch["items_processed"] for batch in successful_batches)
    avg_processing_time = sum(batch["processing_time_seconds"]
                              for batch in successful_batches) / len(successful_batches) if successful_batches else 0

    return {
        "message": f"Async data stream processed {batches} batches concurrently",
        "user": current_user,
        "stream_results": {
            "configuration": {
                "batch_size": batch_size,
                "total_batches": batches,
                "base_processing_delay": processing_delay
            },
            "execution": {
                "total_duration_seconds": round(total_duration, 3),
                "average_batch_processing_time": round(avg_processing_time, 3),
                "concurrent_execution": True,
                "successful_batches": len(successful_batches),
                "total_items_processed": total_items
            },
            "batches": successful_batches,
            "performance_metrics": {
                "throughput_items_per_second": round(total_items / total_duration if total_duration > 0 else 0, 2),
                "efficiency_gain": f"~{round((batches * avg_processing_time) / total_duration if total_duration > 0 else 1, 1)}x faster than sequential",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
        },
        "environment": ENVIRONMENT,
        "note": "This demonstrates concurrent async batch processing with performance optimization"
    }


@router.get("/async-workflow")
async def async_workflow(
    workflow_complexity: str = Query(
        default="medium", regex="^(simple|medium|complex)$", description="Workflow complexity level"),
    current_user: dict = Depends(get_current_user)
):
    """Demonstrate a complex async workflow with multiple stages."""

    complexity_config = {
        "simple": {"stages": 3, "base_delay": 0.05, "parallel_tasks": 2},
        "medium": {"stages": 5, "base_delay": 0.08, "parallel_tasks": 3},
        "complex": {"stages": 7, "base_delay": 0.12, "parallel_tasks": 4}
    }

    config = complexity_config[workflow_complexity]
    start_time = datetime.now()
    workflow_results = []

    for stage in range(1, config["stages"] + 1):
        stage_start = datetime.now()

        # Create parallel tasks for each stage
        async def stage_task(task_id: int) -> dict:
            task_start = datetime.now()
            delay = config["base_delay"] * \
                (1 + (stage * 0.1) + (task_id * 0.05))
            await asyncio.sleep(delay)
            task_end = datetime.now()

            return {
                "task_id": task_id,
                "stage": stage,
                "duration_seconds": round((task_end - task_start).total_seconds(), 3),
                "result": f"Stage {stage} Task {task_id} completed",
                "timestamp": task_end.isoformat()
            }

        # Execute parallel tasks for this stage
        stage_tasks = [
            asyncio.create_task(stage_task(task_id))
            for task_id in range(1, config["parallel_tasks"] + 1)
        ]

        task_results = await asyncio.gather(*stage_tasks)
        stage_end = datetime.now()
        stage_duration = (stage_end - stage_start).total_seconds()

        workflow_results.append({
            "stage": stage,
            "parallel_tasks": config["parallel_tasks"],
            "stage_duration_seconds": round(stage_duration, 3),
            "tasks": task_results,
            "stage_completed_at": stage_end.isoformat()
        })

    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    total_tasks = config["stages"] * config["parallel_tasks"]

    return {
        "message": f"Complex async workflow '{workflow_complexity}' completed successfully",
        "user": current_user,
        "workflow": {
            "complexity": workflow_complexity,
            "configuration": config,
            "execution_summary": {
                "total_stages": config["stages"],
                "total_tasks": total_tasks,
                "total_duration_seconds": round(total_duration, 3),
                "average_stage_duration": round(total_duration / config["stages"], 3),
                "tasks_per_second": round(total_tasks / total_duration if total_duration > 0 else 0, 2)
            },
            "stages": workflow_results,
            "timing": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "efficiency": f"Processed {total_tasks} tasks across {config['stages']} stages"
            }
        },
        "environment": ENVIRONMENT,
        "note": "This demonstrates multi-stage async workflows with parallel task execution"
    }


@router.get("/async-monitor")
async def async_monitor(
    monitor_duration: int = Query(
        default=10, ge=5, le=30, description="Monitoring duration in iterations"),
    check_interval: float = Query(
        default=0.15, ge=0.05, le=0.5, description="Interval between checks"),
    current_user: dict = Depends(get_current_user)
):
    """Real-time async monitoring simulation with live metrics."""

    start_time = datetime.now()
    monitoring_data = []

    async def collect_system_metrics(iteration: int) -> dict:
        """Simulate collecting system metrics asynchronously."""
        check_start = datetime.now()

        # Simulate varying response times for different metrics
        await asyncio.sleep(check_interval * (0.8 + (iteration % 3) * 0.1))

        check_end = datetime.now()
        response_time = (check_end - check_start).total_seconds()

        # Generate realistic-looking metrics
        base_cpu = 25 + (iteration * 2) + (iteration % 7) * 5
        cpu_usage = min(95, max(10, base_cpu + (iteration % 11) * 3))

        memory_base = 45 + (iteration * 1.5)
        memory_usage = min(90, max(20, memory_base + (iteration % 5) * 4))

        return {
            "iteration": iteration,
            "timestamp": check_end.isoformat(),
            "response_time_ms": round(response_time * 1000, 1),
            "metrics": {
                "cpu_usage_percent": round(cpu_usage, 1),
                "memory_usage_percent": round(memory_usage, 1),
                "active_connections": 12 + (iteration % 8),
                "requests_per_minute": 150 + (iteration * 5) + (iteration % 13) * 10,
                "async_tasks_running": 3 + (iteration % 4)
            },
            "status": "healthy" if cpu_usage < 80 and memory_usage < 85 else "warning",
            "iteration_duration_seconds": round(response_time, 3)
        }

    # Collect metrics in real-time
    for i in range(1, monitor_duration + 1):
        iteration_start = datetime.now()

        # Create monitoring task
        metrics_task = asyncio.create_task(collect_system_metrics(i))

        # Simulate other concurrent monitoring activities
        async def background_check():
            await asyncio.sleep(check_interval * 0.3)
            return {"background_task": f"check_{i}", "status": "completed"}

        background_task = asyncio.create_task(background_check())

        # Wait for both tasks
        metrics, background = await asyncio.gather(metrics_task, background_task)

        iteration_end = datetime.now()
        iteration_time = (iteration_end - iteration_start).total_seconds()

        monitoring_data.append({
            **metrics,
            "background_checks": background,
            "total_iteration_time": round(iteration_time, 3)
        })

    end_time = datetime.now()
    total_monitoring_time = (end_time - start_time).total_seconds()

    # Calculate monitoring statistics
    avg_response_time = sum(item["response_time_ms"]
                            for item in monitoring_data) / len(monitoring_data)
    avg_cpu = sum(item["metrics"]["cpu_usage_percent"]
                  for item in monitoring_data) / len(monitoring_data)
    avg_memory = sum(item["metrics"]["memory_usage_percent"]
                     for item in monitoring_data) / len(monitoring_data)

    warnings = [item for item in monitoring_data if item["status"] == "warning"]

    return {
        "message": f"Real-time async monitoring completed - {monitor_duration} iterations",
        "user": current_user,
        "monitoring_session": {
            "configuration": {
                "duration_iterations": monitor_duration,
                "check_interval_seconds": check_interval,
                "total_monitoring_time": round(total_monitoring_time, 3)
            },
            "live_data": monitoring_data,
            "session_summary": {
                "total_checks": len(monitoring_data),
                "average_response_time_ms": round(avg_response_time, 1),
                "monitoring_efficiency": f"{round((monitor_duration * check_interval) / total_monitoring_time * 100, 1)}%",
                "system_health": {
                    "average_cpu_percent": round(avg_cpu, 1),
                    "average_memory_percent": round(avg_memory, 1),
                    "warnings_detected": len(warnings),
                    "overall_status": "healthy" if len(warnings) < monitor_duration * 0.3 else "needs_attention"
                }
            },
            "performance_analysis": {
                "concurrent_operations": "background checks + metrics collection",
                "async_efficiency": "Real-time monitoring with minimal blocking",
                "scalability": f"Processed {monitor_duration * 2} async operations",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
        },
        "environment": ENVIRONMENT,
        "note": "This demonstrates real-time async monitoring with concurrent data collection"
    }


@router.get("/stream-progress")
async def stream_progress(
    total_steps: int = Query(default=10, ge=1, le=50,
                             description="Total number of steps to process"),
    step_delay: float = Query(
        default=0.5, ge=0.1, le=3.0, description="Delay between steps in seconds"),
    current_user: dict = Depends(get_current_user)
):
    """Stream processing progress with real-time updates - designed for streaming UI."""

    # This endpoint is specifically designed to work with the streaming frontend component
    # It returns the complete result but structures it to support progressive display

    start_time = datetime.now()
    processing_steps = []

    for step in range(1, total_steps + 1):
        step_start = datetime.now()

        # Simulate varying work complexity
        work_complexity = 1 + (step * 0.1) + (step % 3) * 0.2
        actual_delay = step_delay * work_complexity

        # Simulate actual async work
        await asyncio.sleep(actual_delay)

        step_end = datetime.now()
        step_duration = (step_end - step_start).total_seconds()

        # Create step result
        step_result = {
            "step": step,
            "status": "completed",
            "progress_percent": round((step / total_steps) * 100, 1),
            "step_duration_seconds": round(step_duration, 3),
            "complexity_factor": round(work_complexity, 2),
            "simulated_work": f"Processing item batch {step}: {'⚡' * min(step, 5)} complexity {work_complexity:.1f}",
            "timestamp": step_end.isoformat(),
            "cumulative_time": round((step_end - start_time).total_seconds(), 3),
            "estimated_remaining": round((total_steps - step) * step_delay * 1.1, 1) if step < total_steps else 0
        }

        processing_steps.append(step_result)

    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()

    return {
        "message": f"Stream processing completed - {total_steps} steps in {total_duration:.2f}s",
        "user": current_user,
        "stream_processing": {
            "configuration": {
                "total_steps": total_steps,
                "step_delay_seconds": step_delay,
                "actual_duration": round(total_duration, 3),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            },
            # This array can be processed incrementally by the frontend
            "progress_data": processing_steps,
            "summary": {
                "average_step_duration": round(total_duration / total_steps, 3),
                "total_items_processed": total_steps,
                "processing_rate": round(total_steps / total_duration, 2),
                "efficiency_score": min(100, round((total_steps * step_delay) / total_duration * 100, 1))
            }
        },
        "frontend_hint": {
            "streaming_compatible": True,
            "progressive_field": "stream_processing.progress_data",
            "step_identifier": "step",
            "completion_indicator": "status"
        },
        "environment": ENVIRONMENT,
        "note": "This endpoint is optimized for streaming frontend components"
    }


@router.get("/live-metrics")
async def live_metrics(
    metric_count: int = Query(
        default=15, ge=5, le=30, description="Number of metric snapshots to collect"),
    collection_interval: float = Query(
        default=0.3, ge=0.1, le=1.0, description="Interval between metric collections"),
    current_user: dict = Depends(get_current_user)
):
    """Collect live system metrics for real-time monitoring dashboard."""

    start_time = datetime.now()
    metrics_snapshots = []

    for snapshot in range(1, metric_count + 1):
        snapshot_start = datetime.now()

        # Simulate metric collection with varying response times
        collection_delay = collection_interval * (0.8 + (snapshot % 4) * 0.1)
        await asyncio.sleep(collection_delay)

        snapshot_end = datetime.now()

        # Generate realistic-looking metrics
        base_values = {
            'cpu': 20 + (snapshot * 1.5) + (snapshot % 7) * 8,
            'memory': 40 + (snapshot * 0.8) + (snapshot % 5) * 6,
            'disk': 60 + (snapshot % 3) * 4,
            'network_in': 50 + (snapshot * 2) + (snapshot % 9) * 15,
            'network_out': 30 + (snapshot * 1.2) + (snapshot % 6) * 8
        }

        # Add some randomness and keep within realistic bounds
        snapshot_data = {
            "snapshot": snapshot,
            "timestamp": snapshot_end.isoformat(),
            "collection_time_ms": round((snapshot_end - snapshot_start).total_seconds() * 1000, 1),
            "metrics": {
                "cpu_usage_percent": min(95, max(5, round(base_values['cpu'], 1))),
                "memory_usage_percent": min(90, max(15, round(base_values['memory'], 1))),
                "disk_usage_percent": min(85, max(30, round(base_values['disk'], 1))),
                "network_in_mbps": round(base_values['network_in'], 1),
                "network_out_mbps": round(base_values['network_out'], 1),
                "active_connections": 10 + (snapshot % 12),
                "response_time_ms": round(50 + (snapshot % 8) * 10 + collection_delay * 100, 1)
            },
            "status": "normal" if base_values['cpu'] < 80 and base_values['memory'] < 80 else "warning",
            "elapsed_seconds": round((snapshot_end - start_time).total_seconds(), 2)
        }

        metrics_snapshots.append(snapshot_data)

    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()

    # Calculate statistics
    avg_cpu = sum(s["metrics"]["cpu_usage_percent"]
                  for s in metrics_snapshots) / len(metrics_snapshots)
    avg_memory = sum(s["metrics"]["memory_usage_percent"]
                     for s in metrics_snapshots) / len(metrics_snapshots)
    warnings = len([s for s in metrics_snapshots if s["status"] == "warning"])

    return {
        "message": f"Live metrics collection completed - {metric_count} snapshots over {total_duration:.2f}s",
        "user": current_user,
        "live_monitoring": {
            "configuration": {
                "snapshot_count": metric_count,
                "collection_interval_seconds": collection_interval,
                "total_duration": round(total_duration, 3),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            },
            "metrics_data": metrics_snapshots,  # Progressive data for streaming
            "session_analysis": {
                "average_cpu_percent": round(avg_cpu, 1),
                "average_memory_percent": round(avg_memory, 1),
                "warning_count": warnings,
                "data_quality": "excellent" if warnings < metric_count * 0.3 else "good",
                "collection_efficiency": round((metric_count * collection_interval) / total_duration * 100, 1)
            }
        },
        "frontend_hint": {
            "streaming_compatible": True,
            "progressive_field": "live_monitoring.metrics_data",
            "step_identifier": "snapshot",
            "real_time_updates": True
        },
        "environment": ENVIRONMENT,
        "note": "Real-time metrics perfect for dashboard streaming"
    }
