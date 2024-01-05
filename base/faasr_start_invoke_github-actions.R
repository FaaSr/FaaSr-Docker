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
.faasr <- fromJSON(get_github_raw(token=token))
.faasr$InvocationID <- Sys.getenv("INPUT_ID")
.faasr$FunctionInvoke <- Sys.getenv("INPUT_INVOKENAME")
.faasr$FaaSrLog <- Sys.getenv("INPUT_FAASRLOG")

# Replace secrets to faasr
faasr_source <- FaaSr::faasr_replace_values(.faasr, secrets)

# back to json format
.faasr <- toJSON(faasr_source, auto_unbox = TRUE)
funcname <- faasr_source$FunctionList[[faasr_source$FunctionInvoke]]$FunctionName

# get files from Git repository
gits <- faasr_source$FunctionGitRepo[[funcname]]
faasr_install_git_repo(gits)

# install CRAN packages
packages <- faasr_source$FunctionCRANPackage[[funcname]]
faasr_install_cran(packages)

# install Git packages
ghpackages <- faasr_source$FunctionGitHubPackage[[funcname]]
faasr_install_git_package(ghpackages)

# source R files
faasr_source_r_files()

# start FaaSr
FaaSr::faasr_start(.faasr)

