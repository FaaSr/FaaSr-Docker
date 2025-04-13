import json
import FaaSr_py
from .faasr_start_invoke_helper import *

def main():
    secrets = os.getenv("SECRET_PAYLOAD")
    token = os.getenv("GITHUB_PAT")
    faasr_json = os.getenv("PAYLOAD")

    payload_data = json.loads(faasr_json)
    secrets_data = json.loads(secrets)

    full_payload = FaaSr_py.graph_functions.faasr_replace_values(payload_data, secrets_data)

    faasr = FaaSr_py.faasr_start(full_payload)

    curr_action = faasr["FunctionInvoke"]
    funcname = faasr["FunctionList"][curr_action]["FunctionName"]
    imported_functions = faasr_func_dependancy_install(faasr, funcname)

    faasr.run_user_function(imported_functions)

    faasr.trigger()

    msg_1 = '{\"faasr\":\"Finished execution of user function ' + curr_action + '\"}\n'
    print(msg_1)
    FaaSr_py.faasr_log(msg_1)
    msg_2 = '{\"faasr\":\"Action Invocation ID is ' + full_payload["InvocationID"] +'\"}\n'
    print(msg_2)
    FaaSr_py.faasr_log(msg_2)


if __name__ == "__main__":
    main()

