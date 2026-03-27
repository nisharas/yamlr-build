import subprocess
import time

start = time.time()
# Start the process, it will wait for input in the Magic Moment
proc = subprocess.Popen(["python", "-m", "yamlr"], cwd="d:\\yamlr", stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Give it some time to render the panel
time.sleep(2) 

# Terminate
proc.terminate()
end = time.time()

print(f"Total time elapsed: {end - start:.2f}s")
