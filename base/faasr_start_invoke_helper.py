import requests
import os
import tarfile
import sys
import string
import random
import subprocess
import re
import base64
import importlib
import FaaSr_py



def faasr_get_github_clone(url, base_dir="/tmp"):
    """
    Downloads a github repo clone from the repo url
    """
    # regex to check that path is github url
    pattern = r"([^/]+/[^/]+)\.git$"
    repo_match = re.search(pattern, url)

    # extract repo name if match is found
    if repo_match:
        repo_name = re.sub(r"\.git$", "", repo_match.group(1))
    else:
        # if path doesn't match, then create random repo name
        repo_name = "".join(
            random.choice(string.ascii_lowercase + string.digits) for _ in range(8)
        )

    repo_path = f"{base_dir}/{repo_name}"

    if os.path.isdir(repo_path):
        import shutil

        shutil.rmtree(repo_path)

    # clone repo using subprocess command
    clone_command = ["git", "clone", "--depth=1", url, repo_path]
    check = subprocess.run(clone_command, text=True)

    # check return code for git clone command. If non-zero, then throw error
    if check.returncode != 0:
        err_msg = f'{{"faasr_install_git_repo":"no repo found, check repository url: {url}"}}'
        print(err_msg)
        sys.exit(1)


def faasr_get_github(faasr_source, path):
    """
    Downloads a repo specified by a github path [username/repo] to a tarball file
    """
    # ensure path has two parts [username/repo]
    parts = path.split("/")
    if len(parts) < 2:
        err_msg = '{"faasr_install_git_repo":"github path should contain at least two parts"}\n'
        print(err_msg)
        sys.exit(1)

    # construct gh url
    username = parts[0]
    reponame = parts[1]
    repo = f"{username}/{reponame}"

    if len(parts) > 2:
        path = "/".join(parts[2:])
    else:
        path = None

    url = f"https://api.github.com/repos/{repo}/tarball"
    tar_name = f"/tmp/{reponame}.tar.gz"

    # send get request
    response1 = requests.get(
        url,
        headers={
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        stream=True,
    )

    # if the response code is 200 (successful), then write the content of the repo to the tarball file
    if response1.status_code == 200:
        with open(tar_name, "wb") as f:
            for chunk in response1.iter_content(chunk_size=8192):
                f.write(chunk)

        with tarfile.open(tar_name) as tar:
            root_dir = tar.getnames()[0]

            if path:
                extract_path = os.path.join(root_dir, path)
                members = [
                    m for m in tar.getmembers() if m.name.startswith(extract_path)
                ]
                tar.extractall(path=f"/tmp/functions{faasr_source['InvocationID']}", members=members)
            else:
                tar.extractall(path=f"/tmp/functions{faasr_source['InvocationID']}")

        os.remove(tar_name)

        msg = '{"faasr_install_git_repo":"Successful"}\n'
        print(msg)
    elif response1.status_code == 401:
        err_msg = '{"faasr_install_git_repo":"Bad credentials - check github token"}\n'
        print(err_msg)
        sys.exit(1)
    else:
        err_msg = f'{{"faasr_install_git_repo": "Not found - check github repo: {username}/{repo}"}}\n'
        print(err_msg)
        sys.exit(1)


def faasr_get_github_raw(token=None, path=None):
    """
    Gets the contents of a single file on GitHub

    @return GitHub file (str)
    """

    if path is None:
        github_repo = os.getenv("PAYLOAD_REPO")
    else:
        github_repo = path

    parts = path.split("/")
    if len(parts) < 3:
        err_msg = '{"faasr_get_github_raw":"github path should contain at least three parts"}\n'
        print(err_msg)
        sys.exit(1)

    # construct gh url
    username = parts[0]
    reponame = parts[1]
    repo = f"{username}/{reponame}"
    branch = parts[2]
    filepath = "/".join(parts[3:])
    url = f"https://api.github.com/repos/{username}/{reponame}/contents/{filepath}?ref={branch}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # send get requests
    if path is None:
        response1 = requests.get(url, headers=headers)
    else:
        headers["Authorization"] = f"token{path}"
        response1 = requests.get(url, headers=headers)

    if response1.status_code == 200:
        msg = '{"faasr_install_git_repo":"Successful"}\n'
        print(msg)
        data = response1.json()
        content = data.get("content", "")
        decoded_bytes = base64.b64decode(content)
        decoded_string = decoded_bytes.decode("utf-8")
        return decoded_string
    elif response1.status_code == 401:
        err_msg = '{"faasr_install_git_repo":"Bad credentials - check github token"}\n'
        print(err_msg)
        sys.exit(1)
    else:
        err_msg = f'{{"faasr_install_git_repo":"Not found - check github repo: {repo}/{path}"}}\n'
        print(err_msg)
        sys.exit(1)


def faasr_install_git_repos(faasr_source, type, gits):
    """
    Downloads content from git repo(s)
    """
    print(f"gits: {gits}")
    if isinstance(gits, str):
        gits = [gits]
    if not gits:
        print('{"faasr_install_git_repo":"No git repo dependency"}\n')
    else:
        # download content from each path
        for path in gits:
            # if path is a repo, clone the repo
            if (
                path.endswith("git")
                or path.startswith("https://")
                or path.startswith("git@")
                or path.startswith("git+")
            ):
                msg = f'{{"faasr_install_git_repo":"get git repo files: {path}"}}\n'
                print(msg)
                faasr_get_github_clone(path)
            else:
                # if path is a python file, download
                file_name = os.path.basename(path)
                if ((file_name.endswith(".py") and type == "Python")
                    or (file_name.endswith(".R") and type == "R")):
                    msg = f'{{"faasr_install_git_repo":"get git repo files: {path}"}}\n'
                    print(msg)
                    content = faasr_get_github_raw(path=path)
                    # write fetched file to disk
                    with open(file_name, "w") as f:
                        f.write(content)
                else:
                    # if the path is a non-python file, download the repo
                    msg = f'{{"faasr_install_git_repo":"get git repo files: {path}"}}\n'
                    print(msg)
                    faasr_get_github(faasr_source, path)


def faasr_pip_install(package):
    """
    Pip installs a single PyPI package

    Returns the name used to source package
    """
    # run pip install [package] command
    if not package:
        print("{\"faasr_install_PyPI\":\"No PyPI package dependency\"}\n")
    else:
        command = ["pip", "install", "--no-input", package]
        subprocess.run(command, text=True)


def faasr_install_cran(package, lib_path = None):
    """
    Installs a single cran package

    Returns the name used to source package
    """
    if not package:
        print("{\"faasr_install_cran\":\"No CRAN package dependency\"}\n")
    else:
        print(f"{{\"faasr_install_cran\":\"Install CRAN package {package}\"}}\n")
        if lib_path:
            lib_path = f'"{lib_path}"'
        else:
            lib_path = ".libPaths()[1]"
        command = ["Rscript", "-e", f'install.packages("{package}", lib={lib_path}, repos="https://cloud.r-project.org")']
        subprocess.run(command, text=True)


def faasr_pip_gh_install(path):
    """
    Installs a single package specified via a github path (name/path) using pip

    Returns the name used to source package
    """
    parts = path.split("/")
    if len(parts) < 2:
        err_msg = '{"faasr_pip_install":"github path should contain at least two parts"}\n'
        print(err_msg)
        sys.exit(1)

    # construct gh url
    username = parts[0]
    reponame = parts[1]
    repo = f"{username}/{reponame}"
    gh_url = f"git+https://github.com/{repo}.git"

    command = ["pip", "install", "--no-input", gh_url]
    subprocess.run(command, text=True)

    # assumes that repo name and module name are the same
    return reponame


def faasr_install_git_packages(gh_packages, type, lib_path=None):
    """
    Install a list of git packages

    Returns names used to source packages (list)
    """
    if not gh_packages:
        print('{"faasr_install_git_package":"No git package dependency"}\n')
    else:
        # install each package
        for package in gh_packages:
            print(f'{{"faasr_install_git_package":"Install Github package {package}"}}\n')
            if type == "Python":
                faasr_pip_gh_install(package)
            elif type == "R":
                if lib_path:
                    lib_path = f'"{lib_path}"'
                else:
                    lib_path = ".libPaths()[1]"
                command = ["Rscript", "-e", f'withr::with_libpaths(new={lib_path}, devtools::install_github("{package}", force=TRUE))']
                subprocess.run(command, text=True)


def faasr_func_dependancy_install(faasr_source, funcname, func_type, new_lib=None):
    # get files from git repo
    gits = faasr_source["FunctionGitRepo"].get(funcname)
    faasr_install_git_repos(faasr_source, func_type, gits)

    if "PyPIPackageDownloads" in faasr_source and func_type == "Python":
        pypi_packages = faasr_source["PyPIPackageDownloads"][funcname]
        for package in pypi_packages:
            faasr_pip_install(package)
    elif "FunctionCRANPackage" in faasr_source and func_type == "R":
        cran_packages = faasr_source["FunctionCRANPackage"][funcname]
        for package in cran_packages:
            faasr_install_cran(package)

    # install gh packages
    if "FunctionGitHubPackage" in faasr_source:
        gh_packages = faasr_source["FunctionGitHubPackage"][funcname]
        faasr_install_git_packages(gh_packages, func_type)



