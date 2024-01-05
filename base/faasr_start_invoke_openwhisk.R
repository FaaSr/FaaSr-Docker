#!/usr/local/bin/Rscript

#' @title Set an entrypoin / Source R codes - for Openwhisk and AWS lambda
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
faasr_source <- fromJSON(.faasr)
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

