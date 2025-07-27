import json
import uuid
import os
import time
import sys
import logging
from multiprocessing import Process
from FaaSr_py import (FaaSrPayload, Scheduler, Executor, faasr_log, global_config, S3LogSender)


def get_payload_from_env():
    """
    Get payload from env
    """
    payload_url = os.getenv("PAYLOAD_URL")
    overwritten = json.loads(os.getenv("OVERWRITTEN"))

    faasr_payload = FaaSrPayload(payload_url, overwritten)
    curr_func = faasr_payload["FunctionInvoke"]
    if faasr_payload["FunctionList"][curr_func].get("UseSecretStore"):
        secrets = os.getenv("SECRET_PAYLOAD")
        faasr_payload.faasr_replace_values(secrets)
    return faasr_payload


def main():
    """
    FaaSr entry point:

    Process payload
    Validate DAG, ensure datastores are accesible
    Initialize log and InvocationID if needed
    Fetch user function, install dependencies, run user function
    Trigger subsequent functions in the workflow
    """
    # get payload
    faasr_payload = get_payload_from_env()
    if not global_config.SKIP_WF_VALIDATE:
        faasr_payload.start()

    global_config.add_s3_log_handler(faasr_payload)

    # for testing
    if not faasr_payload["InvocationID"]: 
        faasr_payload["InvocationID"] = str(uuid.uuid4()) 

    # run user function
    function_executor = Executor(faasr_payload)
    curr_function = faasr_payload["FunctionInvoke"]
    function_result = function_executor.run_func(curr_function)

    # trigger next functions
    scheduler = Scheduler(faasr_payload)
    scheduler.trigger(function_result)

    # flush s3 log singleton
    log_sender = S3LogSender()
    log_sender.flush_log()

if __name__ == "__main__":
    main()



