#!/usr/bin/env python3
import json
import logging
import os
import sys
import uuid
from datetime import datetime

import boto3
from FaaSr_py import Executor, FaaSrPayload, S3LogSender, Scheduler, global_config

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
        elif key.lower().endswith("pat"):
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


def get_secret(key, faasr_payload=None):
    """
    Retrieve a single secret from environment variable
    """
    logger.info(f"DEBUG: get_secret called for key: {key}")
    platform = os.getenv("FAASR_PLATFORM")
    logger.info(f"DEBUG: Platform: {platform}")

    if platform is None:
        raise ValueError("FaaSr Environment Errror: FAASR_PLATFORM not set")
    else:
        platform = platform.lower()

    match platform:
        case "gcp":
            try:
                from google.cloud import secretmanager
                
                logger.info(f"DEBUG: GCP case - getting project ID for key: {key}")
                
                # Get project ID from payload
                curr_func = faasr_payload["FunctionInvoke"]
                logger.info(f"DEBUG: Current function from FunctionInvoke: {curr_func}")
                
                # Check if curr_func exists in ActionList
                available_actions = list(faasr_payload["ActionList"].keys())
                logger.info(f"DEBUG: Available actions in ActionList: {available_actions}")
                
                if curr_func not in faasr_payload["ActionList"]:
                    logger.error(f"DEBUG: Function '{curr_func}' not found in ActionList!")
                    logger.info("DEBUG: Attempting to handle prefixed function name...")
                    
                    # Try to strip workflow prefix
                    workflow_name = faasr_payload.get("WorkflowName", "")
                    logger.info(f"DEBUG: Workflow name: {workflow_name}")
                    
                    if workflow_name and curr_func.startswith(f"{workflow_name}-"):
                        original_func = curr_func.replace(f"{workflow_name}-", "", 1)
                        logger.info(f"DEBUG: Trying original function name: {original_func}")
                        
                        if original_func in faasr_payload["ActionList"]:
                            curr_func = original_func
                            logger.info(f"DEBUG: Using original function name: {curr_func}")
                        else:
                            logger.error(f"DEBUG: Original function '{original_func}' also not found!")
                            return None
                    else:
                        logger.error(f"DEBUG: Cannot resolve function name for: {curr_func}")
                        return None
                
                curr_server = faasr_payload["ActionList"][curr_func]["FaaSServer"]
                logger.info(f"DEBUG: Current server: {curr_server}")
                
                project_id = faasr_payload["ComputeServers"][curr_server]["Namespace"]
                logger.info(f"DEBUG: Project ID resolved: {project_id}")
                
                # Create the Secret Manager client
                client = secretmanager.SecretManagerServiceClient()
                
                # Build the resource name of the secret version
                name = f"projects/{project_id}/secrets/{key}/versions/latest"
                logger.info(f"DEBUG: Accessing secret: {name}")
                
                # Access the secret version
                response = client.access_secret_version(request={"name": name})
                
                secret_value = response.payload.data.decode("UTF-8")
                logger.info(f"DEBUG: Successfully retrieved secret for key: {key} (length: {len(secret_value)})")
                
                # Return the decoded payload (just the raw string, not JSON-parsed)
                return secret_value
                
            except Exception as e:
                logger.warning(f"DEBUG: Exception in get_secret for {key}: {e}")
                logger.warning(f"{key} is missing from GCP Secret Manager: {e}")
                return None


        case "lambda":
            region = os.getenv("AWS_REGION", "us-east-1")
            secret_manager_client = boto3.client(
                service_name="secretsmanager",
                region_name=region,
            )

            secret = secret_manager_client.get_secret_value(SecretId=key).get(
                "SecretString"
            )

            if secret is None:
                logger.warning(f"{key} is missing from AWS Secret Manager")

            return secret
        case "github" | "slurm" | "openwhisk":
            # get secret from env
            secret = os.getenv(key)
            logger.info(f"DEBUG: Environment variable {key} = {'***' if secret else 'None'}")
            if secret is None:
                logger.warning(f"{key} is missing from env")
            return secret
        case _:
            raise ValueError(f"Unsupported platform: {platform}")

    
def fetch_derived_secrets(faasr_payload):
    """
    Fetches secrets from env using keys derived from the datastore and computeserver names
    """
    logger.info("DEBUG: Starting fetch_derived_secrets")
    secrets_dict = {}

    # Compute servers
    logger.info(f"DEBUG: Processing {len(faasr_payload['ComputeServers'])} compute servers")
    for name, fields in faasr_payload["ComputeServers"].items():
        server_type = fields["FaaSType"]
        logger.info(f"DEBUG: Processing server '{name}' of type '{server_type}'")

        match server_type:
            case "GitHubActions":
                key = f"{name}_PAT"
                logger.info(f"DEBUG: Fetching GitHub PAT: {key}")
                secrets_dict[key] = get_secret(key, faasr_payload)

            case "Lambda":
                access_key = f"{name}_AccessKey"
                secret_key = f"{name}_SecretKey"
                logger.info(f"DEBUG: Fetching Lambda secrets: {access_key}, {secret_key}")
                secrets_dict[access_key] = get_secret(access_key, faasr_payload)
                secrets_dict[secret_key] = get_secret(secret_key, faasr_payload)

            case "GoogleCloud":
                secret_key = f"{name}_SecretKey"
                logger.info(f"DEBUG: Fetching GCP secret: {secret_key}")
                secrets_dict[secret_key] = get_secret(secret_key, faasr_payload)

            case "SLURM":
                token = f"{name}_Token"
                logger.info(f"DEBUG: Fetching SLURM token: {token}")
                secrets_dict[token] = get_secret(token,faasr_payload)

            case "OpenWhisk":
                key = f"{name}_APIkey"
                logger.info(f"DEBUG: Fetching OpenWhisk API key: {key}")
                val = get_secret(key,faasr_payload)
                secrets_dict[key] = val
            case _:
                logger.warning(f"Unknown FaaSType for {name}: {server_type}")

    # Data stores
    logger.info(f"DEBUG: Processing {len(faasr_payload['DataStores'])} data stores")
    for name in faasr_payload["DataStores"].keys():
        access_key = f"{name}_AccessKey"
        secret_key = f"{name}_SecretKey"
        logger.info(f"DEBUG: Fetching data store secrets: {access_key}, {secret_key}")
        secrets_dict[access_key] = get_secret(access_key,faasr_payload)
        secrets_dict[secret_key] = get_secret(secret_key,faasr_payload)

    logger.info(f"DEBUG: fetch_derived_secrets completed. Retrieved {len(secrets_dict)} secrets")
    successful_secrets = [k for k, v in secrets_dict.items() if v is not None]
    failed_secrets = [k for k, v in secrets_dict.items() if v is None]
    logger.info(f"DEBUG: Successful secrets: {successful_secrets}")
    logger.info(f"DEBUG: Failed secrets: {failed_secrets}")
    
    return secrets_dict


def get_secrets_from_env(faasr_payload):
    """
    Retrieve secrets from environment variable
    """
    platform = os.getenv("FAASR_PLATFORM").lower()
    logger.info(f"DEBUG: get_secrets_from_env - Platform: {platform}")
    
    curr_func = faasr_payload["FunctionInvoke"]
    logger.info(f"DEBUG: get_secrets_from_env - Current function: {curr_func}")
    
    # Add safety check for ActionList lookup
    if curr_func in faasr_payload["ActionList"]:
        curr_server = faasr_payload["ActionList"][curr_func]["FaaSServer"]
        logger.info(f"DEBUG: get_secrets_from_env - Current server: {curr_server}")
    else:
        logger.error(f"DEBUG: get_secrets_from_env - Function '{curr_func}' not found in ActionList")
        available_actions = list(faasr_payload["ActionList"].keys())
        logger.error(f"DEBUG: Available actions: {available_actions}")
        # This will cause the original error, but now we have debug info
        curr_server = faasr_payload["ActionList"][curr_func]["FaaSServer"]

    match (platform):
        case "github" | "slurm" | "lambda" | "openwhisk" | "gcp":
            # get secrets from env
            logger.info("DEBUG: Calling fetch_derived_secrets")
            secrets_dict = fetch_derived_secrets(faasr_payload)
            return secrets_dict
        case _:
            raise ValueError(f"Unsupported platform: {platform}")


def handle_gcp():
    """Handles GCP payload specifics"""
    payload_url = os.getenv("PAYLOAD_URL")
    overwritten = json.loads(os.getenv("OVERWRITTEN"))

    logger.info(f"DEBUG: handle_gcp - Payload URL: {payload_url}")
    logger.info(f"DEBUG: handle_gcp - Overwritten keys: {list(overwritten.keys())}")
    
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
    logger.info(f"DEBUG: get_payload_from_env - Platform: {platform}")

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
    logger.info(f"DEBUG: get_payload_from_env - FunctionInvoke: {curr_func}")
    
    # Add debug info about ActionList
    action_list_keys = list(faasr_payload["ActionList"].keys())
    logger.info(f"DEBUG: get_payload_from_env - ActionList keys: {action_list_keys}")
    
    if curr_func in faasr_payload["ActionList"]:
        curr_server = faasr_payload["ActionList"][curr_func]["FaaSServer"]
        logger.info(f"DEBUG: get_payload_from_env - Current server: {curr_server}")
    else:
        logger.error(f"DEBUG: get_payload_from_env - CRITICAL: Function '{curr_func}' not in ActionList!")
        logger.error(f"DEBUG: This will cause the NoneType error!")
        # Continue to trigger the original error for now
        curr_server = faasr_payload["ActionList"][curr_func]["FaaSServer"]

    # determine if secrets should be fetched
    # from secret store or overwritten payload
    use_secret_store = faasr_payload["ComputeServers"][curr_server].get("UseSecretStore")
    logger.info(f"DEBUG: get_payload_from_env - UseSecretStore: {use_secret_store}")
    
    if use_secret_store or local_run:
        logger.info("Fetching secrets from secret store")
        logger.info("DEBUG: About to call get_secrets_from_env")

        secrets_dict = get_secrets_from_env(faasr_payload)

        token_present = store_pat_in_env(secrets_dict)
        logger.info(f"DEBUG: Token present after store_pat_in_env: {token_present}")

        logger.info("DEBUG: About to call faasr_payload.replace_secrets")
        faasr_payload.replace_secrets(secrets_dict)
        logger.info("DEBUG: replace_secrets completed")
    else:
        # store token in env for use in fetching file from gh
        token_present = store_pat_in_env(faasr_payload.overwritten["ComputeServers"])
        logger.debug("UseSecretStore off - using overwritten")

    if not token_present:
        logger.info("Without a GitHub PAT in your workflow, you may hit rate limits")
    
    logger.info("DEBUG: get_payload_from_env completed successfully")
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
    logger.info("DEBUG: Handler started")

    # get payload
    faasr_payload = get_payload_from_env(event)
    logger.info("DEBUG: Payload retrieved successfully")

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
    logger.info(f"DEBUG: About to execute function: {curr_function}")
    
    function_result = function_executor.run_func(curr_function, start_time)
    logger.debug(f"Finished execution of {curr_function} with result {function_result}")

    # trigger next functions
    scheduler = Scheduler(faasr_payload)
    scheduler.trigger_all(
        workflow_name=faasr_payload["WorkflowName"], return_val=function_result
    )

    log_sender = S3LogSender.get_log_sender()
    log_sender.flush_log()

    faasr_msg = f"Finished action - InvocationID: {faasr_payload['InvocationID']}"
    logger.info(faasr_msg)


if __name__ == "__main__":
    handler()
