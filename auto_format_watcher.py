import subprocess
import time
import warnings
from contextlib import contextmanager

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

extensions = [".py", ".ipynb", ".yml", ".yaml", ".txt", ".md", ".rst"]


class PausingObserver(Observer):
    def dispatch_events(self, *args, **kwargs):
        if not getattr(self, "_is_paused", False):
            super(PausingObserver, self).dispatch_events(*args, **kwargs)

    def pause(self):
        self._is_paused = True

    def resume(self):
        time.sleep(self.timeout)
        self.event_queue.queue.clear()
        self._is_paused = False

    @contextmanager
    def ignore_events(self):
        self.pause()
        yield
        self.resume()


class ChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        with observer.ignore_events():
            file_path = event.src_path
            if any(file_path for ext in extensions):
                try:
                    cmd = ["pre-commit", "run", "--files", file_path]
                    print(" ".join(cmd))
                    subprocess.run(cmd, check=False)
                except Exception as exc:
                    warnings.warn(f"Failed to run pre-commit on {file_path}:{exc}")


if __name__ == "__main__":
    path = "."
    observer = PausingObserver(timeout=0.125)
    event_handler = ChangeHandler()
    watch = observer.schedule(event_handler, path, recursive=True)
    observer.start()
    print(f"Listening for changes in {path} with " f"extensions {','.join(extensions)}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
