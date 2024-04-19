# LLM Audit README

## Overview
LLM Audit is a CLI tool designed to scan GitHub repositories or local directories for the usage of Large Language Models (LLMs). It aggregates usage statistics, identifies top LLM providers, and generates a comprehensive report.

This tool was built in response to security engineers needing a streamlined way to gather and report on the use of LLMs across codebases in their organization. We quickly built LLM Audit to replace those custom scripts.


## Installation

To install LLM Audit, ensure you have Python 3.8 or higher installed, then run:

`pip install llmaudit`



## Usage

LLM Audit can be used in two modes: scanning GitHub repositories or scanning local directories.

### Scanning GitHub Repositories

To scan GitHub repositories, use the `github` command followed by the repositories you wish to scan. You can specify additional options such as a temporary directory for cloning, whether to keep the cloned repos, and a timeout for cloning.


`llmaudit github [--repos <repo1> <repo2>] [--temp-dir <dir>] [--keep] [--timeout <seconds>]`



- `--repos`: Names of the GitHub repositories to scan. Scans all repos if not specified.
- `--temp-dir`: Temporary directory to clone repositories into. Default is `llm_usage_temp`.
- `--keep`: Keep the temporary folder after cloning. By default, the folder is deleted.
- `--timeout`: Timeout for cloning each repository in seconds. Default is 300 seconds.

### Scanning Local Directories

To scan local directories, use the `local` command followed by the paths to the directories you wish to scan.


`llmaudit local --repos <path1> <path2> ...`


- `--repos`: Paths to the local directories to scan. Required.

## Report Generation

After scanning, LLM Audit generates an HTML report detailing the usage of LLMs across the scanned repositories or directories. The report includes total usage counts, usage by LLM provider, top owners, and statistics by repository.

The report is saved in the `results` directory with a filename that includes the current date, e.g., `llm_usage_report_DD-MM-YYYY.html`.

## Security and Privacy

LLM Audit does not send any data externally. All processing and report generation are done locally on your machine.


## Supported Provider SDKs and Languages

- **Mistral** : Python, JS/TS
- **OpenAI** : Python, JS/TS
- **Anthropic**: Python, JS/TS

## Contributing

Contributions to LLM Audit are welcome! Expanding provider/language and platform support are top of mind, but any other suggestions are welcome!  

## License

LLM Audit is licensed under the Apache Software License. See the LICENSE file for more details.

## Contact

For questions or support, please contact founders@promptarmor.com.
