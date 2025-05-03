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


def faasr_get_github_clone(url):
    """
    Downloads a github repo clone from a the repo url
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

    if os.path.isdir(repo_name):
        import shutil

        shutil.rmtree(repo_name)

    # clone repo using subprocess command
    clone_command = ["git", "clone", "--depth=1", url, repo_name]
    check = subprocess.run(clone_command, text=True)

    # check return code for git clone command. If non-zero, then throw error
    if check.returncode != 0:
        err_msg = '{"faasr_install_git_repo":"no repo found, check repository url: '+ url + '"}'
        print(err_msg)
        sys.exit(1)


def faasr_get_github(faasr_source, path):
    """
    This function downloads a repo specified by a github path [username/repo] to a tarball file
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
                tar.extractall(path=f"/tmp/python-functions{faasr_source['InvocationID']}", members=members)
            else:
                tar.extractall(path=f"/tmp/python-functions{faasr_source['InvocationID']}")

        os.remove(tar_name)

        msg = '{"faasr_install_git_repo":"Successful"}\n'
        print(msg)
    elif response1.status_code == 401:
        err_msg = '{"faasr_install_git_repo":"Bad credentials - check github token"}\n'
        print(err_msg)
        sys.exit(1)
    else:
        err_msg = '{"faasr_install_git_repo": "Not found - check github repo: ' + username + "/" + repo + '"}\n'
        print(err_msg)
        sys.exit(1)


def faasr_get_github_raw(token=None, path=None):
    if path is None:
        github_repo = os.getenv("PAYLOAD_REPO")
    else:
        github_repo = path

    parts = path.split("/")
    if len(parts) < 3:
        # to-do: should these error messages say faasr_install_git_repo?
        err_msg = '{"faasr_install_git_repo":"github path should contain at least three parts"}\n'
        print(err_msg)
        sys.exit(1)

    # construct gh url
    username = parts[0]
    reponame = parts[1]
    repo = f"{username}/{reponame}"
    path = "/".join(parts[2:])
    pat = token
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # send get requests
    if pat is None:
        response1 = requests.get(url, headers=headers)
    else:
        headers["Authorization"] = f"token{pat}"
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
        # to-do: this error is wrong in the original
        err_msg = '{"faasr_install_git_repo":"Not found - check github repo: ' + repo + "/" + path + '"}\n'
        print(err_msg)
        sys.exit(1)


def faasr_install_git_repos(faasr_source, gits):
    """
    This function downloads content from git repo(s)
    """
    if isinstance(gits, str):
        gits = [gits]
    if not gits or len(gits) == 0:
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
                msg = '{"faasr_install_git_repo":"get git repo files: ' + path + '"}\n'
                print(msg)
                faasr_get_github_clone(path)
            else:
                # if path is a python file, download the file and execute the scripts
                file_name = os.path.basename(path)
                if file_name.endswith(".py"):
                    msg = '{"faasr_install_git_repo":"get git repo files: ' + path + '"}\n'
                    print(msg)
                    content = faasr_get_github_raw(path=path)
                    exec(content, globals())
                else:
                    # if the path is a non-python file, download the repo
                    msg = '{"faasr_install_git_repo":"get git repo files: ' + path + '"}\n'
                    print(msg)
                    faasr_get_github(faasr_source, path)


def faasr_pip_install(package):
    # run pip install [package] command
    command = ["pip", "install", package]
    subprocess.run(command, text=True)


def faasr_pip_gh_install(path):
    """
    This function installs a package specified via a github path using pip
    """
    parts = path.split("/")
    if len(parts) < 2:
        err_msg = (
            '{"faasr_pip_install":"github path should contain at least two parts"}\n'
        )
        print(err_msg)
        sys.exit(1)

    # construct gh url
    username = parts[0]
    reponame = parts[1]
    repo = f"{username}/{reponame}"
    gh_url = f"git+https://github.com/{repo}.git"

    command = ["pip", "install", gh_url]
    subprocess.run(command, text=True)


def faasr_install_git_packages(gh_packages, lib_path=None):
    """
    Install a list of git packages
    """
    if not gh_packages or len(gh_packages) == 0:
        print('{"faasr_install_git_package":"No git package dependency"}\n')
    else:
        # install each package
        for package in gh_packages:
            print('{"faasr_install_git_package":"Install Github package' + package + '"}\n')
            faasr_pip_gh_install(package)


def faasr_import_py_files(directory="."):
    """
    This function imports python files in current working directory and returns their functions
    """
    ignore_files = [
        "test_gh_invoke.py",
        "test.py",
        "func_test.py",
        "faasr_start_invoke_helper.py",
        "faasr_start_invoke_openwhisk.py",
        "faasr_start_invoke_aws-lambda.py",
        "faasr_start_invoke_github_actions.py",
    ]
    # convert relative path to absolute path
    directory = os.path.abspath(directory)

    # create dictionary for storing imported functions
    imported_functions = {}

    # add directory to python path
    if directory not in sys.path:
        sys.path.insert(0, directory)

    # walk through  directories and subdirectories
    for root, dirs, files in os.walk(directory):
        # filter for py files
        py_files = [file for file in files if file.endswith(".py")]
        for f in py_files:
            if f not in ignore_files:
                print(f'{{"faasr_source_py_files":"Source python file {f}"}}\n')

                try:
                    rel_path = os.path.relpath(root, directory)
                    if rel_path == ".":
                        # file is in the base directory
                        module_name = os.path.splitext(f)[0]
                    else:
                        # file is in a subdirectory
                        module_path = os.path.join(rel_path, os.path.splitext(f)[0])
                        module_name = module_path.replace(os.path.sep, ".")

                    # import module
                    module = importlib.import_module(module_name)

                    # store functions from module to return
                    for name, obj in module.__dict__.items():
                        if callable(obj) and not name.startswith("_"):
                            imported_functions[name] = obj

                    # update global env with module
                    globals().update(module.__dict__)

                except Exception as e:
                    err_msg = '{"faasr_source_py_files":"python file ' + f + " has following source error: " + str(e) + '"}\n'
                    print(err_msg)
                    sys.exit(1)
    return imported_functions


def faasr_func_dependancy_install(faasr_source, funcname, new_lib=None):
    # get files from git repo
    gits = faasr_source["FunctionGitRepo"][funcname]
    faasr_install_git_repos(faasr_source, gits)

    # to-do: install pypi packages
    if "FunctionPyPIPackage" in faasr_source:
        pypi_packages = faasr_source["FunctionPyPIPackage"][funcname]
        for package in pypi_packages:
            faasr_pip_install(package)

    # install gh packages
    if "FunctionGitHubPackage" in faasr_source:
        gh_packages = faasr_source["FunctionGitHubPackage"][funcname]
        faasr_install_git_packages(gh_packages)

    # source python files
    imported_functions = faasr_import_py_files(f"/tmp/python-functions{faasr_source['InvocationID']}")

    return imported_functions
