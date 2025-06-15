#!/usr/local/bin/Rscript

#' @title Set an entrypoint / Source R codes - for AWS lambda
#' @description When the docker containers run, they start this R code very first time.
#'              This is necessary because it sets library("FaaSr") so that users code can use the FaaSr library and
#'              user's functions would be downloaded from the user's github repository and then they are sourced by
#'              this function. 
#' @param JSON payload is passed as an input when the docker container starts.

library("jsonlite")
library("httr")
library("FaaSr")
source("faasr_start_invoke_helper.R")

# get arguments from stdin
.faasr <- commandArgs(TRUE)

# start FaaSr
.faasr <- FaaSr::faasr_start(.faasr)
if (.faasr[1]=="abort-on-multiple-invocation"){
  q("no")
}

# set a new library path "/tmp": Lambda specific
.libPaths( c(.libPaths(), "/tmp") )
new_lib <- "/tmp"

# Download the dependencies
funcname <- .faasr$FunctionList[[.faasr$FunctionInvoke]]$FunctionName
faasr_dependency_install(.faasr, funcname, new_lib=new_lib)

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
