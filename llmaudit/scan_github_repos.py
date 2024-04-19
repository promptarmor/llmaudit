import os
import shutil
import argparse
from github import Github
import git
from llmaudit import sprawl
from typing import List


def scan_repos(folder_name: str, keep_folder: bool, timeout: int, specified_repos: List):
    # Initialize GitHub client with PyGithub
    token = os.getenv("GITHUB_TOKEN")
    if token == None:
        print("Environment variable GITHUB_TOKEN not found - exiting..")
        exit()


    g = Github(token)

    # Get the authenticated user
    user = g.get_user()

    # Ensure the target directory doesn't already exist (don't want to delete existing files)
    if os.path.exists(folder_name):
        print(f"The folder '{folder_name}' already exists. Exiting...")
        exit()
    else:
        os.makedirs(folder_name)
    # Initialize an empty list to store repository paths
    cloned_repos = []

    # Loop through all repositories of the authenticated user
    for repo in user.get_repos():
        #If a user specified the repos they want to scan, only process those
        if specified_repos and repo.name not in specified_repos:
            continue 
        try:
            print(f"Cloning {repo.name}")
            repo_path = os.path.join(folder_name, repo.name)
            # Use GitPython to clone the repository
            git.Repo.clone_from(repo.clone_url, repo_path, kill_after_timeout=timeout)
            # Append the path of the cloned repository to the repos list
            cloned_repos.append(repo_path)
        except Exception as e:
            print("Exception thrown: ", e)
            print(f"Unable to process repo {repo.name}")

    # Print the list of repository paths
    print("Paths of cloned repositories:", cloned_repos)

    sprawl.run_llm_usage_scanner(repos=cloned_repos, temp_folder_path=folder_name, delete_path=not keep_folder)

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Clone all GitHub repositories for a user into a specified folder using PyGithub and GitPython, with an option to keep or delete the folder afterwards.')
    parser.add_argument('--repos', nargs='+', help='Names of the repo(s) to scan')
    parser.add_argument('--temp-dir', default='llm_usage_temp', help='Specify the temporary directory to clone repositories into (default: llm_usage_temp)')
    parser.add_argument('--keep', action='store_true', help='Keep the temporary folder after cloning (default: False, will delete)')
    parser.add_argument('--timeout', type=int, default=300, help='Timeout for cloning each repository in seconds (default: 300)')  # Add timeout argument

    # Parse arguments
    args = parser.parse_args()


    FOLDER_NAME = args.temp_dir
    KEEP_FOLDER = args.keep
    TIMEOUT = args.timeout
    REPOS = args.repos

    scan_repos(FOLDER_NAME, KEEP_FOLDER, TIMEOUT, REPOS)

