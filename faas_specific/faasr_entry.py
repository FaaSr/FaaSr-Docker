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


def store_pat_in_env():
    """
    Checks if token is present in dict and stores
    in environment variable "TOKEN" if it is
    """
    token = get_secret("GH_PAT")
    if not token:
        logger.warning("GitHub PAT not present; your workflow will not be able to pull from private repos and may hit rate limits") # noqa E501
        return
    os.environ["GH_PAT"] = token

def get_secret(key, faasr_payload=None):
    """
    Retrieve a single secret from environment variable
    """
   
    platform = os.getenv("FAASR_PLATFORM")

    if platform is None:
        raise ValueError("FaaSr Environment Errror: FAASR_PLATFORM not set")
    else:
        platform = platform.lower()

    match platform:
        case "gcp":
            try:
                if faasr_payload is None:
                    logger.warning("cannot fetch secret without the payloadd details")
                    return
                from google.cloud import secretmanager

                # Get project ID from payload
                curr_func = faasr_payload["FunctionInvoke"]
                
                curr_server = faasr_payload["ActionList"][curr_func]["FaaSServer"]
                project_id = faasr_payload["ComputeServers"][curr_server]["Namespace"]
               
                
                # Create the Secret Manager client
                client = secretmanager.SecretManagerServiceClient()
                
                # Build the resource name of the secret version
                name = f"projects/{project_id}/secrets/{key}/versions/latest"
                
                # Access the secret version
                response = client.access_secret_version(request={"name": name})
                
                secret_value = response.payload.data.decode("UTF-8")
                
                # Return the decoded payload (just the raw string, not JSON-parsed)
                return secret_value
                
            except Exception as e:
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
            if secret is None:
                logger.warning(f"{key} is missing from env")
            return secret
        case _:
            raise ValueError(f"Unsupported platform: {platform}")

    
def fetch_derived_secrets(faasr_payload):
    """
    Fetches secrets from env using keys derived from the datastore and computeserver names

    Example keys:
    OW
        OW_APIkey
    AWS
        AWS_AccessKey
        AWS_SecretKey
    GCP
        GCP_SecretKey
    SLURM
        SLURM_Token
    GH
        GH_PAT
    Minio
        Minio_AccessKey
        Minio_SecretKey

    Arguments:
        payload -- faasr payload

    Return:
        secrets dict -- dictionary mapping derived keys to actual secrets
    """
    secrets_dict = {}

    # Compute servers
    for name, fields in faasr_payload["ComputeServers"].items():
        server_type = fields["FaaSType"]

        match server_type:
            case "GitHubActions":
                key = f"{name}_PAT"
                secrets_dict[key] = get_secret(key, faasr_payload)

            case "Lambda":
                access_key = f"{name}_AccessKey"
                secret_key = f"{name}_SecretKey"
                secrets_dict[access_key] = get_secret(access_key, faasr_payload)
                secrets_dict[secret_key] = get_secret(secret_key, faasr_payload)

            case "GoogleCloud":
                secret_key = f"{name}_SecretKey"
                secrets_dict[secret_key] = get_secret(secret_key, faasr_payload)

            case "SLURM":
                token = f"{name}_Token"
                secrets_dict[token] = get_secret(token,faasr_payload)

            case "OpenWhisk":
                key = f"{name}_APIkey"
                val = get_secret(key,faasr_payload)
                secrets_dict[key] = val
            case _:
                logger.warning(f"Unknown FaaSType for {name}: {server_type}")

    # Data stores
    for name in faasr_payload["DataStores"].keys():
        access_key = f"{name}_AccessKey"
        secret_key = f"{name}_SecretKey"
        secrets_dict[access_key] = get_secret(access_key,faasr_payload)
        secrets_dict[secret_key] = get_secret(secret_key,faasr_payload)

    if "VMConfig" in faasr_payload:
        vm_config = faasr_payload["VMConfig"]
        vm_name = vm_config.get("Name")
        
        if vm_name:
            provider = vm_config.get("Provider", "AWS")
            
            if provider == "AWS":
                access_key = f"{vm_name}_AccessKey"
                secret_key = f"{vm_name}_SecretKey"
                secrets_dict[access_key] = get_secret(access_key, faasr_payload)
                secrets_dict[secret_key] = get_secret(secret_key, faasr_payload)

    return secrets_dict


def get_secrets_from_env(faasr_payload):
    """
    Retrieve secrets from environment variable
    """
    platform = os.getenv("FAASR_PLATFORM").lower()
    
    curr_func = faasr_payload["FunctionInvoke"]
    curr_server = faasr_payload["ActionList"][curr_func]["FaaSServer"]

    match (platform):
        case "github" | "slurm" | "lambda" | "openwhisk" | "gcp":
            # get secrets from env
            secrets_dict = fetch_derived_secrets(faasr_payload)
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

    store_pat_in_env()

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

       # token_present = store_pat_in_env(secrets_dict)
        faasr_payload.replace_secrets(secrets_dict)
    else:
        # store token in env for use in fetching file from gh
        #token_present = store_pat_in_env(faasr_payload.overwritten["ComputeServers"])
        logger.debug("UseSecretStore off - using overwritten")

    #if not token_present:
        #logger.info("Without a GitHub PAT in your workflow, you may hit rate limits")
    
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

    if local_run and not faasr_payload.get("InvocationID"):
        faasr_payload["InvocationID"] = str(uuid.uuid4())

    # run user function
    function_executor = Executor(faasr_payload)
    curr_function = faasr_payload["FunctionInvoke"]
    
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