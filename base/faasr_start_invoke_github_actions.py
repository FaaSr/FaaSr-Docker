import json
import FaaSr_py
import uuid
import os
import time
import sys
import requests
from multiprocessing import Process
from FaaSr_py import FaaSr, Scheduler, Executor, faasr_log
from faasr_start_invoke_helper import *
    

def get_env_and_payload():
    """
    (to-do) Get payload and env (from secret store or payload)
    """
    payload_url = os.getenv("PAYLOAD_URL")
    secrets = os.getenv("SECRET_PAYLOAD")

    raw_payload = faasr_get_github_raw(path=payload_url)
    payload_dict = json.loads(raw_payload)

    secrets_data = json.loads(secrets)

    full_payload = FaaSr_py.faasr_replace_values(payload_dict, secrets_data)
    return full_payload 


def run_function(faasr):
    """
    Fetch and run the users function
    """
    # get func type and name
    curr_action = faasr["FunctionInvoke"]
    func_type = faasr["FunctionList"][curr_action]["Type"]
    func_name = faasr["FunctionList"][curr_action]["FunctionName"]

    print('install dependencies')
    faasr_func_dependancy_install(faasr, func_name, func_type)

    function_executor = Executor(faasr)

    # Run function
    try:
        print("starting server")
        function_executor.host_server_api()
        print('run user function')
        function_executor.call()
        print('get function return value')
        function_result = function_executor.get_function_return()
    except SystemExit as e:
        exit_msg = f'{{"faasr_start_invoke_github_actions.py": "ERROR -- non-zero exit code from user function"}}'
        print(exit_msg)
        sys.exit(1)
    except RuntimeError as e:
        err_msg = f'{{"faasr_start_invoke_github_actions.py": "RUNTIME ERROR while running user function -- {e}"}}'
        print(err_msg)
        sys.exit(1)
    except Exception as e:
        err_msg = f'{{"faasr_start_invoke_github_actions.py": ERROR -- MESSAGE: {e}"}}'
        print(err_msg)
        sys.exit(1)
    finally:
        # Clean up server
        print("terminate server process")
        function_executor.terminate_server()
    return function_result


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
    full_payload = get_env_and_payload()
    overwritten = json.loads(os.getenv("OVERWRITTEN"))
    faasr = FaaSr(full_payload, overwritten)
    if not debug_config.SKIP_WF_VALIDATE:
        faasr.validate_payload()

    if not faasr["InvocationID"]: 
        faasr["InvocationID"] = str(uuid.uuid4()) 

    # run user function
    function_result = run_function(faasr)
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


