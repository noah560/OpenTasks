import sys
import subprocess
import signal
import time

print("Starting server...")
server_proc = subprocess.Popen(
    [sys.executable, "server.py"],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=None,
    start_new_session=True
)

print("Waiting 5 seconds for server to finish initializing...")
time.sleep(5)

try:
    import basic_client
except KeyboardInterrupt:
    pass
except EOFError:
    pass
finally:
    print("\nClient stopped. Waiting for server to terminate...")
    server_proc.send_signal(signal.SIGINT)
    server_proc.wait()
    print("Server stopped! Exiting...")
