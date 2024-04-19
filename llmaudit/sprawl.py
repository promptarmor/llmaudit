import os
import re
import json, csv
import argparse
from codeowners import CodeOwners
from typing import Dict, List, Pattern, Tuple
from jinja2 import Environment, FileSystemLoader
import shutil
import datetime

class LLMUsageScanner:
    #Repo -> stats
    stats = dict()
    def __init__(self, root_dir: str, codeowners_path: str = None):
        self.root_dir = root_dir
        codeowners_content = ""
        if codeowners_path:
            try:
                with open(codeowners_path, 'r') as file:
                    codeowners_content = file.read()
            except FileNotFoundError:
                print(f"The CODEOWNERS file at {codeowners_path} was not found. Skipping owner matching.")
                codeowners_content = ""
        self.codeowners_data = CodeOwners(codeowners_content)
        self.language_configs = {
            'python': {
                'extensions': ['.py'],
                'libraries': {
                    'OpenAI': {
                        'import_pattern': r'import\s+openai|from\s+openai\s+import\s+\S+',
                        'init_pattern': r'(\w+)\s*=\s*OpenAI\(\)',
                        'specific': [
                            {'pattern': r'({var_name}\.)?chat\.completions\.create\(', 'name': 'OpenAI: Completion Create'},
                            {'pattern': r'({var_name}\.)?embeddings\.create\(', 'name': 'OpenAI: Embedding Create'},
                        ]
                    },
                    'Anthropic': {
                        'import_pattern': r'import\s+anthropic|from\s+anthropic\s+import\s+\S+',
                        'init_pattern': r'(\w+)\s*=\s*anthropic\.Anthropic\(\)',
                        'specific': [
                            {'pattern': r'({var_name}\.)?messages\.create\(', 'name': 'Anthropic: Message Create'},
                            {'pattern': r'({var_name}\.)?messages\.stream\(', 'name': 'Anthropic: Message Stream'},
                            {'pattern': r'({var_name}\.)?completions\.create\(', 'name': 'Anthropic: Completions Create'},
                        ]
                    },
                    'Mistral': {
                        'import_pattern': r'import\s+mistralai|from\s+mistralai(\.\S+)?\s+import\s+\S+',
                        'init_pattern': r'(\w+)\s*=\s*MistralClient\(',
                        'specific': [
                            {'pattern': r'({var_name}\.)?chat\(', 'name': 'Mistral: Chat'},
                            {'pattern': r'({var_name}\.)?chat_stream\(', 'name': 'Mistral: Chat Stream'},
                            {'pattern': r'({var_name}\.)?embeddings\(', 'name': 'Mistral: Embeddings Create'},
                        ]
                    }
                }
            },
        'javascript': {
        'extensions': ['.js', '.jsx', '.ts', '.tsx'],
        'libraries': {
            'OpenAI': {
                'import_pattern': r'import\s+OpenAI\s+from\s+[\'"]openai[\'"]|const\s+OpenAI\s+=\s+require\([\'"]openai[\'"]\);?',                'init_pattern': r'const\s+(\w+)\s*=\s*new\s+OpenAI\(',
                'specific': [
                {'pattern': r'({var_name}\.)?chat\.completions\.create\(', 'name': 'OpenAI: Completion Create'},
                {'pattern': r'({var_name}\.)?embeddings\.create\(', 'name': 'OpenAI: Embedding Create'},
                ]
            },
            'Anthropic': {
                'import_pattern': r'import\s+Anthropic\s+from\s+\'@anthropic-ai/sdk\'|const\s+Anthropic\s+=\s+require\(\'@anthropic-ai/sdk\'\);',
                'init_pattern': r'const\s+(\w+)\s*=\s*new\s+Anthropic\(',
                'specific': [
                    {'pattern': r'({var_name}\.)?messages\.create\(', 'name': 'Anthropic: Message Create'},
                    {'pattern': r'({var_name}\.)?messages\.stream\(', 'name': 'Anthropic: Message Stream'},
                    {'pattern': r'({var_name}\.)?completions\.create\(', 'name': 'Anthropic: Completions Create'},
                ]
            },
            'Mistral': {
                'import_pattern': r'import\s+MistralClient\s+from\s+\'@mistralai/mistralai\'|const\s+MistralClient\s+=\s+require\(\'@mistralai/mistralai\'\);',
                'init_pattern': r'const\s+(\w+)\s*=\s*new\s+MistralClient\(',
                'specific': [
                    {'pattern': r'({var_name}\.)?chat\(', 'name': 'Mistral: Chat'},
                    {'pattern': r'({var_name}\.)?chat_stream\(', 'name': 'Mistral: Chat Stream'},
                    {'pattern': r'({var_name}\.)?embeddings\(', 'name': 'Mistral: Embeddings Create'},
                ]
            }
        }
    }
        }
        self.results_by_file = {}
        self.results = []

    def scan(self):
        for root, dirs, files in os.walk(self.root_dir):
            for file in files:
                for language, config in self.language_configs.items():
                    if any(file.endswith(ext) for ext in config['extensions']):
                        file_path = os.path.join(root, file)
                        self.results_by_file[file_path] = []
                        self._scan_file(file_path, config['libraries'])

        LLMUsageScanner._write_csv(self.results, 'results/results.csv')
        LLMUsageScanner.stats[self.root_dir] = self._calc_statistics()
        
    
    def _parse_codeowners(self) -> List[Tuple[str, List[str]]]:
        codeowners = []
        with open(self.codeowners_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split()
                    pattern = parts[0]
                    owners = parts[1:]
                    codeowners.append((pattern, owners))
        return codeowners


    def _find_codeowners(self, file_path: str) -> List[str]:
        codeowners = self.codeowners_data.of(file_path)
        return codeowners
    
    def _scan_file(self, file_path: str, libraries: Dict):
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

            for library, patterns in libraries.items():
                if re.search(patterns['import_pattern'], content):
                    var_name = self._find_init_client_name(content, patterns.get('init_pattern', ''))
                    is_exact_match = var_name != ""
                    updated_specifics = self._update_specific_patterns(patterns['specific'], var_name)
                    self._scan_for_specific_usage(content, updated_specifics, file_path, library, is_exact_match)

    def _find_init_client_name(self, content: str, init_pattern: str) -> str:
        match = re.search(init_pattern, content)
        return match.group(1) if match else ''

    def _update_specific_patterns(self, specifics: List[Dict], var_name: str) -> List[Dict]:
        return [{'pattern': specific['pattern'].format(var_name=var_name if var_name else ''), 'name': specific['name']} for specific in specifics]

    def _scan_for_specific_usage(self, content: str, specifics: List[Dict], file_path: str, library: str, exact_match: bool):
        for specific in specifics:
            self._find_usage(content, specific['pattern'], file_path, library, specific['name'], exact_match)

    def _prev_results_has_conflicting_exact_match(self, line_number: int, file_path: str, curr_match_is_exact: bool) -> bool:
        index_to_delete = None
        for index, prev_res in enumerate(self.results_by_file[file_path]):
            if prev_res['line'] == line_number and prev_res['exact_match']:
                return True
            if prev_res['line'] == line_number and not prev_res['exact_match']:
                # Mark the index for deletion if the current match is an exact match
                if curr_match_is_exact:
                    index_to_delete = index
        
        # If an index was marked for deletion, remove that item from the list
        if index_to_delete is not None:
            del self.results_by_file[file_path][index_to_delete]
            # After removing, there's no conflicting exact match, so return False
            return False
        
        return False
    
    def _find_usage(self, content: str, pattern: str, file_path: str, library: str, label: str, exact_match: bool) -> bool:
        found = False
        for match in re.finditer(pattern, content):
            found = True
            line_number = self._get_line_number(content, match.start())
            
            owners = ()
            if self.codeowners_data != "":
                owners = self._find_codeowners(file_path)
            #Check if the same line has been found before in this file with an exact match
            has_conflicting_match = self._prev_results_has_conflicting_exact_match(line_number, file_path, exact_match)

            #If there is a conflicting result on the same line and the current match is not an exact match
            if has_conflicting_match and not exact_match:
                return False

            result = {
                'line': line_number,
                'pattern': pattern,
                'label': label,
                'owners': owners,
                'exact_match': exact_match,
                'file_path': file_path,
                'library': library
            }
            self.results_by_file[file_path].append(result)
            self.results.append(result)

        return found
    
    def _calc_statistics(self):
        library_counts = {}
        owner_counts = {}  # Use a dict to count occurrences of each owner
        total_results = len(self.results)

        for result in self.results:
            library = result['library']
            if library in library_counts:
                library_counts[library] += 1
            else:
                library_counts[library] = 1
            
            # Aggregate owners
            owners = result.get('owners', [])
            for owner in owners:
                if isinstance(owner, tuple):
                    owner = ', '.join(owner)  # Convert tuple to string if necessary
                if owner in owner_counts:
                    owner_counts[owner] += 1
                else:
                    owner_counts[owner] = 1
        
        # Optionally, return the statistics if you need to use them elsewhere
        return total_results, library_counts, owner_counts


    @staticmethod
    def _get_line_number(content: str, char_index: int) -> int:
        return content.count('\n', 0, char_index) + 1

    @staticmethod
    def _write_csv(data: Dict, file_name: str):
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        file_exists = os.path.isfile(file_name)
        with open(file_name, mode='a' if file_exists else 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            # Write the header only if the file does not exist
            if not file_exists:
                writer.writerow(['Library', 'File Path', 'Line Number', 'Pattern', 'Label', 'Owners', 'Exact Match', 'Secured?'])
            for result in data:
                writer.writerow([
                    result['library'],
                    result['file_path'],
                    result['line'],
                    result['pattern'],
                    result['label'],
                    result['owners'],  # Assuming owners is a list
                    result['exact_match']
                ])

    @staticmethod
    def _aggregate_usage():
        total_usage_by_library = {}
        total_usages = 0
        owner_usage = {}

        for _, repo_stats in LLMUsageScanner.stats.items():
            total_usages += repo_stats[0]  # Total usages for the repo
            library_counts = repo_stats[1]  # Library counts
            for library, count in library_counts.items():
                total_usage_by_library[library] = total_usage_by_library.get(library, 0) + count

            owner_info = repo_stats[2]  # Set of owners
            for owner, usage_count in owner_info.items():
                if owner in owner_usage:
                    owner_usage[owner] += usage_count
                else:
                    owner_usage[owner] = usage_count

        # Identifying top owners based on the number of occurrences across repos
        top_owners = sorted(owner_usage.items(), key=lambda x: x[1], reverse=True)

        return {"total_usage_by_library": total_usage_by_library, "total_usages": total_usages, "top_owners": top_owners}
    
    @staticmethod
    def generate_report():
        template_dir = os.path.dirname(__file__)
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('report_template.html')

        aggregate_stats = LLMUsageScanner._aggregate_usage()
        repo_stats = {repo_name: {"total_usages": stats[0], 
                                  "library_counts": stats[1], 
                                  "owner_counts": dict(sorted(stats[2].items(), key=lambda item: item[1], reverse=True)[:3])}
                      for repo_name, stats in LLMUsageScanner.stats.items()}

        # Render the template with data
        rendered_report = template.render(**aggregate_stats, repo_stats=repo_stats)

        # Save the rendered HTML to a file
        current_date = datetime.datetime.now().strftime("%d-%m-%Y")
        report_name = "results/llm_usage_report_" + current_date + ".html"
        with open(report_name, 'w') as f:
            f.write(rendered_report)

        print(f"Success! View your report at: {report_name}")
        print("You can also find a CSV of all the results in the same directory!")



def run_llm_usage_scanner(repos : List, temp_folder_path="", delete_path: bool = False):
    codeowners_paths = ['.github/CODEOWNERS', 'docs/CODEOWNERS', '.gitlab/CODEOWNERS', 'CODEOWNERS']
        
    for repo in repos:
        if not os.path.isdir(repo):
            print(f"Error: The repository path {repo} does not exist. Skipping...")
            continue

        codeowners_path_found = None
        for potential_path in codeowners_paths:
            full_path = os.path.join(repo, potential_path)
            if os.path.exists(full_path):
                codeowners_path_found = full_path
                break
        if codeowners_path_found:
            scanner = LLMUsageScanner(root_dir=repo, codeowners_path=codeowners_path_found)
        else:
            print(f"No CODEOWNERS file found in {repo}. Proceeding without CODEOWNERS.")
            scanner = LLMUsageScanner(root_dir=repo)
        


        #Run the scan
        scanner.scan()
        
        # Delete the repo if specified
        if delete_path:
            try:
                shutil.rmtree(repo)
                print(f"Deleted repository: {repo}")
            except Exception as e:
                print(f"Error deleting repository {repo}: {e}")

    #Generate a report
    LLMUsageScanner.generate_report()
    
    # Delete the temporary folder after generating the report, if delete_path is True
    if delete_path and temp_folder_path:
        try:
            shutil.rmtree(temp_folder_path)
            print(f"Deleted temporary folder: {temp_folder_path}")
        except Exception as e:
            print(f"Error deleting temporary folder {temp_folder_path}: {e}")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scan for LLM library usage and check CODEOWNERS.')
    parser.add_argument('repos', nargs='+', help='Root directory of the repo(s) to scan')
    args = parser.parse_args()

    run_llm_usage_scanner(args.repos)