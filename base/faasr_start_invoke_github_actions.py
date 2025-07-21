import json
import uuid
import os
import time
import sys
import requests
from multiprocessing import Process
from FaaSr_py import (FaaSr, Scheduler, Executor, faasr_log, validate_payload, global_config)


# testing
from FaaSr_py.s3_api.put_file import faasr_put_file
from pathlib import Path

def get_env_and_payload():
    """
    (to-do) -- url part of faasr class
    (to-do) -- from secret store or payload
    Get payload and env
    """
    payload_url = os.getenv("PAYLOAD_URL")
    secrets = json.loads(os.getenv("SECRET_PAYLOAD"))
    overwritten = json.loads(os.getenv("OVERWRITTEN"))

    faasr = FaaSr(payload_url, overwritten)
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
    # get payload
    faasr = get_env_and_payload()
    if not global_config.SKIP_WF_VALIDATE:
        validate_payload(faasr)

    # for testing
    if not faasr["InvocationID"]: 
        faasr["InvocationID"] = str(uuid.uuid4()) 

    # run user function
    function_executor = Executor(faasr)
    curr_function = faasr["FunctionInvoke"]
    print(f"CURR FUNC: {curr_function}")
    function_result = function_executor.run_func(curr_function)
    print(function_result)
    msg_1 = f'{{\"faasr\":\"Finished execution of user function\"}}\n'
    print(msg_1)
    faasr_log(faasr, msg_1)

    # trigger next functions
    scheduler = Scheduler(faasr)
    scheduler.trigger(function_result)
    
    msg_2 = f'{{\"faasr\":\"Action Invocation ID is {faasr["InvocationID"]}\"}}\n'
    print(msg_2)
    faasr_log(faasr, msg_2)


if __name__ == "__main__":
    main()



