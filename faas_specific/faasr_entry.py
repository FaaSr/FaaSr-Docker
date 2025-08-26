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
local_run = False


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
    return


def get_secrets_from_secret_manager(project_id, secret_name):
    """
    Retrieve secrets from GCP Secret Manager
    """
    try:

        from google.cloud import secretmanager

        # Create the Secret Manager client
        client = secretmanager.SecretManagerServiceClient()

        # Build the resource name of the secret version
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"

        # Access the secret version
        response = client.access_secret_version(request={"name": name})

        # Return the decoded payload
        return json.loads(response.payload.data.decode("UTF-8"))
    except Exception as e:
        logger.error(f"Error accessing Secret Manager: {e}")
        # Fallback to environment variable if available
        secrets = os.getenv("SECRET_PAYLOAD")
        if secrets:
            logger.info("Falling back to SECRET_PAYLOAD environment variable")
            return json.loads(secrets)
        return {}


def get_secrets_from_env(faasr_payload):
    """
    Retrieve secrets from environment variable
    """
    platform = os.getenv("FAASR_PLATFORM").lower()
    curr_func = faasr_payload["FunctionInvoke"]
    curr_server = faasr_payload["ActionList"][curr_func]["FaaSServer"]

    match (platform):
        case "gcp":
            project_id = faasr_payload["ComputeServers"][curr_server]["Namespace"]

            # Get secret name from environment or use default
            secret_name = os.getenv("GCP_SECRET_NAME", "faasr-secrets")

            # Get secrets from Secret Manager
            secrets_dict = get_secrets_from_secret_manager(project_id, secret_name)
        case "github" | "slurm" | "lambda" | "openwhisk":
            # get secrets from env
            secrets = os.getenv("SECRET_PAYLOAD")
            if secrets:
                secrets_dict = json.loads(secrets)
            else:
                logger.critical("No SECRET_PAYLOAD found in environment")
                raise ValueError("No SECRET_PAYLOAD found in environment")
        case _:
            raise ValueError(f"Unsupported platform: {platform}")
    return secrets_dict


def handle_gcp():
    """Handles GCP payload specifics"""
    payload_url = os.getenv("PAYLOAD_URL")
    overwritten = json.loads(os.getenv("OVERWRITTEN"))

    logger.debug(f"Payload URL: {payload_url}")
    return FaaSrPayload(payload_url, overwritten)


def handle_slurm():
    """Handles SLURM payload specifics"""
    payload_url = os.getenv("PAYLOAD_URL")
    overwritten = json.loads(os.getenv("OVERWRITTEN", "{}"))

    logger.debug(f"Payload URL: {payload_url}")
    return FaaSrPayload(payload_url, overwritten)


def handle_lambda(lambda_event):
    """Handles AWS Lambda payload specifics"""
    # change to /tmp for lambda
    os.chdir("/tmp")

    if not lambda_event:
        raise ValueError("Lambda event not provided")
    payload_url = lambda_event["PAYLOAD_URL"]
    overwritten = json.loads(lambda_event["OVERWRITTEN"])

    logger.debug(f"Payload URL: {payload_url}")
    return FaaSrPayload(payload_url, overwritten)


def handle_ow():
    """Handles OpenWhisk payload specifics"""
    # Get payload from command line argument
    payload = json.loads(sys.argv[1])

    payload_url = payload["PAYLOAD_URL"]
    overwritten = payload["OVERWRITTEN"]

    logger.debug(f"Payload URL: {payload_url}")

    return FaaSrPayload(payload_url, overwritten)


def handle_gh():
    """Handles GitHub Actions payload specifics"""
    payload_url = os.getenv("PAYLOAD_URL")
    overwritten = json.loads(os.getenv("OVERWRITTEN"))

    logger.debug(f"Payload URL: {payload_url}")
    return FaaSrPayload(payload_url, overwritten)


def get_payload_from_env(lambda_event=None):
    """
    Get payload from env
    """
    platform = os.getenv("FAASR_PLATFORM").lower()

    if not platform:
        raise ValueError("FAASR_PLATFORM environment variable not set")

    match (platform):
        case "github":
            faasr_payload = handle_gh()
        case "openwhisk":
            faasr_payload = handle_ow()
        case "lambda":
            faasr_payload = handle_lambda(lambda_event)
        case "slurm":
            faasr_payload = handle_slurm()
        case "gcp":
            faasr_payload = handle_gcp()
        case _:
            raise ValueError(f"Unsupported platform: {platform}")

    curr_func = faasr_payload["FunctionInvoke"]
    curr_server = faasr_payload["ActionList"][curr_func]["FaaSServer"]

    # determine if secrets should be fetched
    # from secret store or overwritten payload
    if faasr_payload["ComputeServers"][curr_server].get("UseSecretStore") or local_run:
        logger.info("Fetching secrets from secret store")

        secrets_dict = get_secrets_from_env(faasr_payload)

        token_present = store_pat_in_env(secrets_dict)

        faasr_payload.faasr_replace_values(secrets_dict)
    else:
        # store token in env for use in fetching file from gh
        token_present = store_pat_in_env(faasr_payload.overwritten["ComputeServers"])
        logger.debug("UseSecretStore off - using overwritten")

    if not token_present:
        logger.info("Without a GitHub PAT in your workflow, you may hit rate limits")
    return faasr_payload


def handler(event=None, context=None):
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
    faasr_payload = get_payload_from_env(event)

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

    faasr_msg = f"Finished action - InvocationID: {faasr_payload['InvocationID']}"
    logger.info(faasr_msg)


if __name__ == "__main__":
    handler()
