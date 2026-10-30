import os
import subprocess
import sys
import time

from application import main as application_main
from client import BaseClient
from payload import Payload
from router import BaseRouter
from full_server import FullServer



def main():
    server = FullServer().start()
    router1 = BaseRouter(server.address, port=10655).start()
    router2 = BaseRouter(server.address, port=10656).start()
    router3 = BaseRouter(server.address, port=10657).start()
    application_processes = []

    r1_addr = router1.address
    r2_addr = router2.address
    r3_addr = router3.address

    server_addr = server.address

    print(f"Server address: {server_addr}")
    print(f"Router 1 address: {r1_addr}")
    print(f"Router 2 address: {r2_addr}")
    print(f"Router 3 address: {r3_addr}")

    try:
        application_path = os.path.join(os.path.dirname(__file__), "application.py")
        application_environment = os.environ.copy()
        application_environment["MESSENGER_ROUTER_ADDRESS"] = r1_addr
        if getattr(sys, "frozen", False):
            application_command = [sys.executable, "--client"]
            application_cwd = os.path.dirname(sys.executable)
        else:
            application_command = [sys.executable, application_path, "--client"]
            application_cwd = os.path.dirname(application_path)
        for _ in range(2):
            application_processes.append(
                subprocess.Popen(
                    application_command,
                    cwd=application_cwd,
                    env=application_environment,
                )
            )
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Stopping nodes")
    finally:
        for application_process in application_processes:
            application_process.terminate()
        for application_process in application_processes:
            application_process.wait()
        router1.stop()
        router2.stop()
        router3.stop()
        server.stop()


if __name__ == "__main__":
    if "--client" in sys.argv:
        application_main()
    else:
        main()
