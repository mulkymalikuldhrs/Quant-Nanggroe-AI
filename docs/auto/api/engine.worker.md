# engine.worker

## Class: 

Background task status.

*Line: 53*

---

## Class: 

Worker lifecycle state.

*Line: 64*

---

## Class: 

Health check result for the background worker.

Attributes:
    worker_id: Unique worker identifier.
    state: Current worker state.
    uptime_seconds: Seconds since worker started.
    tasks_running: Number of currently running tasks.
    tasks_completed: Total tasks completed successfully.
    tasks_failed: Total tasks that failed.
    last_error: Last error message (if any).
    lock_held: Whether the singleton lock is held.
    timestamp: UTC timestamp.

**Methods:** to_api_dict

*Line: 77*

---

## Class: 

Metrics for a single background task.

Attributes:
    task_name: Name of the task.
    status: Current status.
    run_count: Number of times the task has run.
    success_count: Number of successful runs.
    failure_count: Number of failed runs.
    last_run_at: Timestamp of last run.
    last_duration_ms: Duration of last run in milliseconds.
    last_error: Last error message.
    next_run_at: Estimated next run time.

*Line: 121*

---

## Class: 

Definition of a background task.

Attributes:
    name: Task name (must be unique).
    func: Async callable to execute.
    interval_seconds: How often to run the task.
    timeout_seconds: Maximum execution time before cancellation.
    max_retries: Maximum retry attempts on failure.
    retry_backoff_base: Base delay (seconds) for exponential backoff.
    retry_backoff_max: Maximum backoff delay (seconds).
    enabled: Whether the task is active.

*Line: 153*

---

## Class: 

File-based singleton lock.

Ensures only one worker instance runs at a time by creating
and locking a file.  The lock is automatically released when
the process exits.

Args:
    lock_path: Path to the lock file.
    worker_id: Unique worker identifier.

**Methods:** __init__, acquire, release, is_held

*Line: 180*

---

## Class: 

Singleton background worker with configurable task management.

Acquires a file-based singleton lock to ensure only one instance
runs at a time.  Manages a list of configurable background tasks
with retry logic, exponential backoff, and graceful shutdown.

Args:
    worker_id: Unique identifier (auto-generated if None).
    lock_path: Path for the singleton lock file.
    tasks: List of WorkerTask definitions.

Usage::

    worker = BackgroundWorker(
        tasks=[
            WorkerTask(name="price_fetch", func=fetch_prices, interval=60),
            WorkerTask(name="rebalance_check", func=check_rebalance, interval=300),
        ]
    )
    await worker.start()

**Methods:** __init__, register_task, deregister_task, _default_tasks, _register_signal_handlers, health_check, task_metrics, state, stats

*Line: 273*

---

## Function: 

Convert to API-safe dictionary.

*Line: 106*

---

## Function: 

*Line: 192*

---

## Function: 

Try to acquire the singleton lock.

Returns:
    True if lock acquired, False if another instance holds it.

*Line: 202*

---

## Function: 

Release the singleton lock.

*Line: 244*

---

## Function: 

Whether this worker holds the lock.

*Line: 265*

---

## Function: 

*Line: 296*

---

## Function: 

Register a background task.

Args:
    task: WorkerTask definition.

Raises:
    ValueError: If a task with the same name already exists.

*Line: 319*

---

## Function: 

Remove a registered task.

Args:
    name: Task name.

Returns:
    True if the task was found and removed.

*Line: 336*

---

## Function: 

Create default background tasks.

Tasks can be overridden via QNAI_WORKER_TASKS env var
(comma-separated task names).

*Line: 352*

---

## Function: 

Register SIGINT/SIGTERM handlers for graceful shutdown.

*Line: 618*

---

## Function: 

Get current worker health status.

Returns:
    WorkerHealth with current status.

*Line: 635*

---

## Function: 

Get metrics for all registered tasks.

*Line: 660*

---

## Function: 

Current worker state.

*Line: 665*

---

## Function: 

Worker statistics.

*Line: 670*

---

## Function: 

*Line: 622*

---

