import multiprocessing
import os
from dotenv import load_dotenv

load_dotenv()

# Gunicorn configuration
host = os.getenv("HOST", "0.0.0.0")
port = os.getenv("PORT", "8000")
bind = f"{host}:{port}"

# Worker configuration
# For deep learning models, you typically want fewer workers than a standard web app
# as each worker loads a copy of the model (unless shared memory is used carefully).
# We'll default to 1 worker to save memory, or use the number of CPU cores if preferred.
workers = int(os.getenv("GUNICORN_WORKERS", 1))
worker_class = "uvicorn.workers.UvicornWorker"
timeout = int(os.getenv("GUNICORN_TIMEOUT", 120))

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
