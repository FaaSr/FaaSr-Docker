import json
import uuid
import os
import logging
from datetime import datetime
from google.cloud import secretmanager

from FaaSr_py import (FaaSrPayload, Scheduler, Executor, global_config, S3LogSender)

logger = logging.getLogger("FaaSr_py")
local_run = False

def get_secrets_from_secret_manager(project_id, secret_name):
    """
    Retrieve secrets from GCP Secret Manager
    """
    try:
        # Create the Secret Manager client
        client = secretmanager.SecretManagerServiceClient()
        
        # Build the resource name of the secret version
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        
        # Access the secret version
        response = client.access_secret_version(request={"name": name})
        
        # Return the decoded payload
        return json.loads(response.payload.data.decode('UTF-8'))
    except Exception as e:
        logger.error(f"Error accessing Secret Manager: {e}")
        # Fallback to environment variable if available
        secrets = os.getenv("SECRET_PAYLOAD")
        if secrets:
            logger.info("Falling back to SECRET_PAYLOAD environment variable")
            return json.loads(secrets)
        return {}

def get_payload_from_env():
    """
    Get payload from env - with GCP Secret Manager integration
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
        logger.info("Fetching secrets from GCP Secret Manager")
        
        # Get project ID from compute server config
        project_id = curr_server["Namespace"]
        
        # Get secret name from environment or use default
        secret_name = os.getenv("GCP_SECRET_NAME", "faasr-secrets")
        
        # Get secrets from Secret Manager
        secrets_dict = get_secrets_from_secret_manager(project_id, secret_name)
        
        # Replace values in the payload
        faasr_payload.faasr_replace_values(secrets_dict)
    else:
        logger.info("UseSecretStore off -- using overwritten")
    
    return faasr_payload

def main():
    """
    FaaSr entry point for GCP:
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

    faasr_msg = f"Finished action -- InvocationID: {faasr_payload['InvocationID']}"
    logger.info(faasr_msg)

if __name__ == "__main__":
    main()
