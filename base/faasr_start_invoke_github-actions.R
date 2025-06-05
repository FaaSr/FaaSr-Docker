#' @title Set an entrypoin / Prepare parameters / Source R codes - for Github actions
#' @description When the docker containers run, they start this R code very first time.
#'              This is necessary because it sets library("FaaSr") so that users code can use the FaaSr library and
#'              user's functions would be downloaded from the user's github repository and then they are sourced by
#'              this function. In case of github actions, Secrets(Credentials) for S3(storage), Lambda, Openwhisk, and
#'              Github actions itself and Payload should be called by "replace_values" and "get_payload".
#' @param secrets should be stored in the github repository as secrets.
#' @param JSON payload should be stored in the github repository and the path should be designated.

library("httr")
library("jsonlite")
library("FaaSr")
source("faasr_start_invoke_helper.R")

# get arguments from environments
secrets <- fromJSON(Sys.getenv("SECRET_PAYLOAD"))
token <- Sys.getenv("GITHUB_PAT")
.faasr <- Sys.getenv("PAYLOAD")

if (.faasr == ""){
  .faasr <- fromJSON(faasr_get_github_raw(token=token))
} else {
  .faasr <- fromJSON(.faasr)
}

# Replace secrets to faasr
.faasr <- FaaSr::faasr_replace_values(.faasr, secrets)

# back to json format
.faasr <- toJSON(.faasr, auto_unbox = TRUE)

# start FaaSr
.faasr <- FaaSr::faasr_start(.faasr)
if (.faasr[1]=="abort-on-multiple-invocation"){
  q("no")
}

# Download the dependencies
funcname <- .faasr$FunctionList[[.faasr$FunctionInvoke]]$FunctionName
faasr_dependency_install(.faasr, funcname)

# Execute User function
.faasr <- FaaSr::faasr_run_user_function(.faasr)

# Trigger the next functions
FaaSr::faasr_trigger(.faasr)

# Leave logs
msg_1 <- paste0('{\"faasr\":\"Finished execution of User Function ',.faasr$FunctionInvoke,'\"}', "\n")
cat(msg_1)
result <- faasr_log(msg_1)
msg_2 <- paste0('{\"faasr\":\"With Action Invocation ID is ',.faasr$InvocationID,'\"}', "\n")
cat(msg_2)
result <- faasr_log(msg_2)
