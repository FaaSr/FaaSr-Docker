import json
import uuid
import os
import time
import sys
import logging
from multiprocessing import Process
from FaaSr_py import (FaaSrPayload, Scheduler, Executor, faasr_log, global_config, S3LogSender)


def get_env_and_payload():
    """
    (to-do) -- url part of faasr class
    (to-do) -- from secret store or payload
    Get payload and env
    """
    payload_url = os.getenv("PAYLOAD_URL")
    secrets = json.loads(os.getenv("SECRET_PAYLOAD"))
    overwritten = json.loads(os.getenv("OVERWRITTEN"))

    faasr = FaaSrPayload(payload_url, overwritten)
    faasr.faasr_replace_values(secrets)

    return faasr 
    

def main():
    """
    FaaSr entry point:

    Process payload
    Validate DAG, ensure datastores are accesible
    Initialize log and InvocationID if needed
    Fetch user function, install dependencies, run user function
    Trigger subsequent functions in the workflow
    """
    log_sender = S3LogSender()

    # get payload
    faasr_payload = get_env_and_payload()
    if not global_config.SKIP_WF_VALIDATE:
        faasr_payload.start()

    # run user function
    function_executor = Executor(faasr_payload)
    curr_function = faasr_payload["FunctionInvoke"]
    function_result = function_executor.run_func(curr_function)

    # trigger next functions
    scheduler = Scheduler(faasr_payload)
    scheduler.trigger(function_result)

    log_sender.flush_log()

if __name__ == "__main__":
    main()



