import subprocess
import json
import sys
import shutil
import os
def handler(event, context):
    if os.path.exists('/tmp/action'):
        shutil.rmtree('/tmp/action')
        
    # Copy the entire action directory to /tmp/action directory
    shutil.copytree("/action", "/tmp/action")

    event_str = json.dumps(event)
    
    result = subprocess.run(["Rscript", "/tmp/action/faasr_start_invoke_aws-lambda.R", event_str],
                        capture_output=True,
                        text=True,
                        cwd='/tmp/action')
    
    # Store R script stdout and stderr
    stdout = result.stdout
    stderr = result.stderr

    # Print R script output
    print("R script output:")
    print(stdout)

    # aws lambda will keep the execution environment for several minutes to reduce pre-warm time
    if os.path.exists('/tmp/action'):
        shutil.rmtree('/tmp/action')

    if result.returncode != 0:
        print("R script error output:")
        print(stderr, file=sys.stderr)
        raise Exception(f"Error executing R script. Stdout: {stdout}, Stderr: {stderr}")

    return stdout

