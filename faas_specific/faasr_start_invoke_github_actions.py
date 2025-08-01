import json
import uuid
import os
import logging

from datetime import datetime
from FaaSr_py import (FaaSrPayload, Scheduler, Executor, global_config, S3LogSender)


logger = logging.getLogger("FaaSr_py")
local_run = False


def store_pat_in_env(dictionary):
    """
    Checks if token is present in dict and stores
    in environment variable "TOKEN" if it is
    """
    for key, val in dictionary.items():
        if key.endswith("TOKEN"):
            os.environ["TOKEN"] = val
            return True
    return False

def get_payload_from_env():
    """
    Get payload from env
    """
    payload_url = os.getenv("PAYLOAD_URL")
    overwritten = json.loads(os.getenv("OVERWRITTEN"))

    logger.debug(f"Payload URL: {payload_url}")
    faasr_payload = FaaSrPayload(payload_url, overwritten)

    curr_func = faasr_payload["FunctionInvoke"]
    curr_server = faasr_payload["ActionList"][curr_func]["FaaSServer"]

    # determine if secrets should be fetched 
    # from secret store or overwritten payload
    if faasr_payload["ComputeServers"][curr_server].get("UseSecretStore") or local_run:
        logger.info("Fetching secrets from secret store")

        # get secrets from env
        secrets = os.getenv("SECRET_PAYLOAD")
        secrets_dict = json.loads(secrets)
        token_present = store_pat_in_env(secrets_dict)
        faasr_payload.faasr_replace_values(secrets_dict)
    else:
        # store token in env for use in fetching file from gh
        token_present = store_pat_in_env(overwritten)
        logger.info("UseSecretStore off -- using overwritten")

    if not token_present:
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
    logger.debug(f"Finished execution of {curr_function} with result {function_result}")

    # trigger next functions
    scheduler = Scheduler(faasr_payload)
    scheduler.trigger_all(function_result)

    log_sender = S3LogSender.get_log_sender()
    log_sender.flush_log()

    faasr_msg = f"Finished action -- InvocationID: {faasr_payload["InvocationID"]}"
    logger.info(faasr_msg)

if __name__ == "__main__":
    main()



