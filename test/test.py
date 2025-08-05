import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from base import faasr_start_invoke_helper


def test_script():
    url = "https://github.com/FaaSr/FaaSr-tutorial.git"
    faasr_start_invoke_helper.faasr_get_github_clone(url)

    path = "FaaSr/FaaSr-tutorial"
    faasr_start_invoke_helper.faasr_get_github(path)

    py_file_path = "nolcut/FaaSr-synthetic/translator/convert.py"
    raw_tutorial = faasr_start_invoke_helper.faasr_get_github_raw(path=py_file_path)
    with open("raw_file.txt", "w") as f:
        f.write(raw_tutorial)

    gits = [
        "https://github.com/black-parrot/black-parrot.git",
        "nolcut/FaaSr-synthetic/translator/workflow.py",
        "black-parrot/black-parrot-sim/Makefile.env",
    ]
    faasr_start_invoke_helper.faasr_install_git_repos(gits)

    pip_package = "boto3"
    faasr_start_invoke_helper.faasr_pip_install(pip_package)

    package_repo_path = "psf/requests"
    faasr_start_invoke_helper.faasr_pip_gh_install(package_repo_path)

    packages = ["wfcommons/WfCommons", "pwaller/pyfiglet", "tartley/colorama"]
    faasr_start_invoke_helper.faasr_install_git_packages(packages)

    faasr_start_invoke_helper.faasr_import_py_files()
    faasr_start_invoke_helper.print_hello_world()


if __name__ == "__main__":
    test_script()
