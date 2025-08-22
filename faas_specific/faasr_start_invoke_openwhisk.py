#!/usr/bin/env python3
import json
import logging
import os
import sys
import uuid
from datetime import datetime

from FaaSr_py import (Executor, FaaSrPayload, S3LogSender, Scheduler,
                      global_config)

logger = logging.getLogger("FaaSr_py")
local_run = True


def store_pat_in_env(dictionary):
    """
    Checks if token is present in dict and stores
    in environment variable "TOKEN" if it is
    """
    for key, val in dictionary.items():
        if isinstance(val, dict):
            if store_pat_in_env(val):
                return True
        elif key.lower().endswith("token"):
            os.environ["TOKEN"] = val
            return True
    return False


def get_payload_from_env():
    """
    Get payload from env
    """
    payload = json.loads(sys.argv[1])

    payload_url = payload["PAYLOAD_URL"]
    overwritten = payload["OVERWRITTEN"]

    logger.debug(f"Payload URL: {payload_url}")
    faasr_payload = FaaSrPayload(payload_url, overwritten)

    # store token in env for use in fetching file from gh
    if "ComputeServers" in overwritten:
        store_pat_in_env(overwritten["ComputeServers"])
        logger.debug("UseSecretStore off -- using overwritten")
    else:
        logger.info("Without a GitHub PAT in your workflow, you may hit rate limits")
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
    try:
        start_time = datetime.now()

        # get payload
        faasr_payload = get_payload_from_env()
        if not global_config.SKIP_WF_VALIDATE:
            faasr_payload.start()
        else:
            logger.info("Skipping WF validation")

        global_config.add_s3_log_handler(faasr_payload, start_time)

        if local_run and not faasr_payload["InvocationID"]:
            faasr_payload["InvocationID"] = str(uuid.uuid4())

        # run user function
        function_executor = Executor(faasr_payload)
        curr_function = faasr_payload["FunctionInvoke"]
        function_result = function_executor.run_func(curr_function, start_time)
        logger.debug(
            f"Finished execution of {curr_function} with result {function_result}"
        )

        # trigger next functions
        scheduler = Scheduler(faasr_payload)
        scheduler.trigger_all(function_result)

        log_sender = S3LogSender.get_log_sender()
        log_sender.flush_log()

        faasr_msg = f"Finished action -- InvocationID: {faasr_payload['InvocationID']}"
        logger.info(faasr_msg)

    except Exception as e:
        print(json.dumps({"test": "testing"}))
        if not isinstance(e, SystemExit):
            logger.error(f"Unexpected error while running OpenWhisk action: {e}")
        return {"result": "fail"}

    print(json.dumps({"test": "testing"}))
    return {"result": "success"}


if __name__ == "__main__":
    main()
