import requests
import json
import FaaSr_py
from faasr_start_invoke_helper import *

secrets = os.getenv("SECRET_PAYLOAD")
token = os.getenv("GITHUB_PAT")
faasr_json = os.getenv("PAYYLOAD")

if faasr_json == "":
    faasr_json = faasr_get_github_raw(token=token)
    
full_payload = faasr_replace_values(json.loads(faasr_json))

faasr = faasr_start(full_payload)

curr_action = full_payload['FunctionInvoke']
funcname = full_payload['FunctionList'][curr_action]['FunctionName']
faasr_func_dependancy_install(full_payload, funcname)

faasr_run_user_function(full_payload)

faasr_trigger(full_payload)

# to-do: log



    

