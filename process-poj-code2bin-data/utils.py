import subprocess
from typing import Iterable
from concurrent.futures import ThreadPoolExecutor, Future

def run_cmd(cmd: Iterable[str]):
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )

    stdout, stderr = process.communicate()

    if process.returncode == 2:
        # print(stderr.decode("utf-8").rstrip())
        # return None
        raise ValueError(stderr.decode("utf-8").rstrip())
    elif process.returncode == 9 or process.returncode == -9:
        # print(f"Program graph construction exceeded {TIMEOUT} seconds")
        # return None
        raise TimeoutError(f"cmd timeout")
    elif process.returncode:
        # print(stderr.decode("utf-8").rstrip())
        # return None
        raise OSError(stderr.decode("utf-8").rstrip())


def run_cmds_parallel(cmds: Iterable[list], num_workers: int = 16):
    def handle_exception(future: Future):
        exp = future.exception()
        if exp:
            print(exp)

    with ThreadPoolExecutor(num_workers) as thread_pool:
        for cmd in cmds:
            print(cmd)
            task = thread_pool.submit(run_cmd, cmd)
            task.add_done_callback(handle_exception)
