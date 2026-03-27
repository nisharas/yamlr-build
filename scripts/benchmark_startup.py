import time
import subprocess
import statistics

def measure_startup(cmd):
    start = time.perf_counter()
    subprocess.run(cmd, capture_output=True, shell=False)
    return (time.perf_counter() - start) * 1000

if __name__ == "__main__":
    commands = [
        ["yamlr", "--version"],
        ["yamlr", "help"]
    ]
    
    for cmd in commands:
        latencies = [measure_startup(cmd) for _ in range(5)]
        avg = statistics.mean(latencies)
        print(f"Command: {' '.join(cmd)}")
        print(f"  Avg Latency: {avg:.2f}ms")
        print(f"  Samples: {[round(l, 2) for l in latencies]}")
