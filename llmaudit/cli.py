import argparse
from llmaudit import scan_github_repos, sprawl

def main_cli():
    parser = argparse.ArgumentParser(description="CLI tool to scan GitHub repos or run sprawl locally.")
    subparsers = parser.add_subparsers(dest='command', required=True, help='Commands')

    # Subparser for scanning GitHub repositories
    github_parser = subparsers.add_parser('github', help='Scan GitHub repositories')
    github_parser.add_argument('--repos', nargs='+', help='Names of the repo(s) to scan (default is all repos)')
    github_parser.add_argument('--temp-dir', default='llm_usage_temp', help='Specify the temporary directory to clone repositories into (default: llm_usage_temp)')
    github_parser.add_argument('--keep', action='store_true', help='Keep the temporary folder after cloning (default: False, will delete)')
    github_parser.add_argument('--timeout', type=int, default=300, help='Timeout for cloning each repository in seconds (default: 300)')  # Add timeout argument


    # Subparser for running sprawl locally
    local_parser = subparsers.add_parser('local', help='Run sprawl locally')
    local_parser.add_argument('--repos', nargs='+', required=True, help='Root directory of the repo(s) to scan')
    

    args = parser.parse_args()

    if args.command == 'github':
        # Assuming scan_github_repos.main() accepts command line arguments directly
        scan_github_repos.scan_repos(args.temp_dir, args.keep, args.timeout, args.repos)
    elif args.command == 'local':
        # Assuming sprawl.main() accepts command line arguments directly
        sprawl.run_llm_usage_scanner(args.repos)

if __name__ == "__main__":
    main_cli()