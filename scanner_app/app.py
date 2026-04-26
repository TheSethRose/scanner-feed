import queue
import signal
import threading

from .audio import FeedWorker
from .config import ensure_output_dirs
from .feeds import load_feeds
from .models import SegmentJob
from .transcribe import transcribe_loop


def main() -> None:
    ensure_output_dirs()
    feeds = load_feeds()
    stop_event = threading.Event()
    jobs: queue.Queue[SegmentJob] = queue.Queue(maxsize=200)

    print("Configured feeds:", flush=True)

    for feed in feeds:
        print(f"  - {feed.name}: {feed.url}", flush=True)

    workers = [
        FeedWorker(feed=feed, jobs=jobs, stop_event=stop_event)
        for feed in feeds
    ]

    for worker in workers:
        worker.start()

    def shutdown(_signum, _frame):
        print("\nStopping...", flush=True)
        stop_event.set()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    transcribe_loop(jobs, stop_event)
