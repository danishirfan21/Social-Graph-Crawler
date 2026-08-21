from prometheus_client import Counter, Histogram, make_asgi_app

frontier_completed = Counter("crawler_frontier_completed_total", "Completed frontier items")
frontier_failed = Counter("crawler_frontier_failed_total", "Failed frontier items")
frontier_retries = Counter("crawler_frontier_retries_total", "Retried frontier items")
worker_tasks = Counter("crawler_worker_tasks_total", "Worker tasks", ["status"])
processing_seconds = Histogram("crawler_frontier_processing_seconds", "Frontier processing duration")
metrics_app = make_asgi_app()
