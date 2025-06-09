#!/usr/bin/env python3
"""
Git Commit Review Page Generator

This script generates a static HTML page similar to Helix Swarm's review page,
but based on Git commits. It extracts commit information from a Git repository
and creates a visually similar review page.
"""

import os
import sys
import argparse
import subprocess
import datetime
import re
import html
import shutil
from pathlib import Path
import json
from render import Render

def is_git_or_svn(repo_path):
    """
    Determine if a repository is Git or SVN.
    
    Args:
        repo_path (str): Path to the repository
        
    Returns:
        str: 'git', 'svn', or 'unknown'
    """
    repo_path = os.path.abspath(repo_path)
    
    # Check for Git repository
    if os.path.isdir(os.path.join(repo_path, '.git')):
        return 'git'
    
    # Check for SVN repository by looking for .svn directory
    if os.path.isdir(os.path.join(repo_path, '.svn')):
        return 'svn'
    
    # Check if any parent directory contains .svn (for SVN working copies)
    current_path = repo_path
    while current_path != os.path.dirname(current_path):  # Stop at root
        if os.path.isdir(os.path.join(current_path, '.svn')):
            return 'svn'
        current_path = os.path.dirname(current_path)
    
    # Try running svn info to see if it's an SVN working copy
    try:
        subprocess.run(['svn', 'info'], cwd=repo_path, check=True, 
                      capture_output=True, text=True)
        return 'svn'
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Try running git status to see if it's a Git repository
    try:
        subprocess.run(['git', 'status'], cwd=repo_path, check=True, 
                      capture_output=True, text=True)
        return 'git'
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    return 'unknown'


class GitCommitReviewGenerator:
    """
    A class to generate a static HTML page for Git commit reviews
    similar to Helix Swarm's review page.
    """
    
    def __init__(self, repo_path, output_dir, commit_hash=None, template_dir=None, scan_results_dir=None):
        """
        Initialize the generator with repository path and output directory.
        
        Args:
            repo_path (str): Path to the Git repository
            output_dir (str): Directory to output the generated HTML files
            commit_hash (str, optional): Specific commit hash to generate review for
            template_dir (str, optional): Directory containing custom templates
            scan_results_dir (str, optional): Directory containing scan results JSON files
        """
        self.repo_path = os.path.abspath(repo_path)
        self.output_dir = os.path.abspath(output_dir)
        self.commit_hash = commit_hash
        self.template_dir = template_dir
        self.scan_results_dir = scan_results_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create assets directory
        self.assets_dir = os.path.join(self.output_dir, 'assets')
        os.makedirs(self.assets_dir, exist_ok=True)
        
        # Initialize renderer
        self.renderer = Render(self.output_dir, self.assets_dir)
        
        # Verify git repository
        if not os.path.isdir(os.path.join(self.repo_path, '.git')):
            raise ValueError(f"Not a valid Git repository: {self.repo_path}")
    
    def load_scan_results(self):
        """
        Load scan results from all JSON files in the scan results directory.
        
        Returns:
            list: Combined scan results from all JSON files
        """
        scan_results = []
        
        if not self.scan_results_dir:
            return scan_results
            
        if not os.path.isdir(self.scan_results_dir):
            print(f"Warning: Scan results directory does not exist: {self.scan_results_dir}")
            return scan_results
        
        try:
            # Find all JSON files in the directory
            json_files = []
            for filename in os.listdir(self.scan_results_dir):
                if filename.lower().endswith('.json'):
                    json_files.append(os.path.join(self.scan_results_dir, filename))
            
            print(f"Found {len(json_files)} JSON files in scan results directory")
            
            # Load and combine results from all JSON files
            for json_file in json_files:
                try:
                    print(f"Loading scan results from: {json_file}")
                    with open(json_file, 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                        
                        # Extract filename from the 'file' field
                        if 'file' not in file_data:
                            print(f"  Warning: No 'file' field found in {json_file}")
                            continue
                            
                        filename = file_data['file']
                        # Convert Windows path to Unix path for consistency
                        filename = filename.replace('\\', '/')
                        # Extract relative path if it's an absolute path
                        if ':' in filename:
                            # Try to extract relative path from absolute Windows path
                            parts = filename.split('/')
                            # Look for common project directory names
                            for i, part in enumerate(parts):
                                if part in ['Server', 'src', 'source', 'code']:
                                    filename = '/'.join(parts[i:])
                                    break
                        
                        source_code = file_data.get('源码', '')
                        
                        # Helper function to parse line number from line range
                        def parse_line_number(line_range, source_code):
                            if '-' in line_range:
                                # Range like "3345-3348", take the starting line
                                return int(line_range.split('-')[0])
                            # if the string is a number
                            elif line_range.isdigit():
                                # Single line number like "3358"
                                return int(line_range)
                            else:
                                # Find first line number in source code
                                import re
                                match = re.search(r'\n(\d+)', source_code)
                                if match:
                                    return int(match.group(1))
                                else:
                                    return 1  # Default to line 1 if no line number found
                        
                        # Collect all issues for this file, then group by line number
                        file_issues = []
                        
                        # Process "可能存在的问题" (general severity)
                        if '可能存在的问题' in file_data:
                            for issue in file_data['可能存在的问题']:
                                line_range = issue.get('行号范围', '1')
                                line_number = parse_line_number(line_range, source_code)
                                
                                file_issues.append({
                                    '文件名': filename,
                                    '行号': line_number,
                                    '问题描述': issue.get('问题描述', ''),
                                    '修改意见': issue.get('修改意见', ''),
                                    '严重程度': '一般'
                                })
                        
                        # Process "肯定存在的问题" (severe)
                        if '肯定存在的问题' in file_data:
                            for issue in file_data['肯定存在的问题']:
                                line_range = issue.get('行号范围', '1')
                                line_number = parse_line_number(line_range, source_code)
                                
                                file_issues.append({
                                    '文件名': filename,
                                    '行号': line_number,
                                    '问题描述': issue.get('问题描述', ''),
                                    '修改意见': issue.get('修改意见', ''),
                                    '严重程度': '严重'
                                })
                        
                        # Group issues by line number and combine them
                        from collections import defaultdict
                        grouped_issues = defaultdict(list)
                        for issue in file_issues:
                            grouped_issues[issue['行号']].append(issue)
                        
                        # Create combined scan results for each line
                        for line_number, issues in grouped_issues.items():
                            # Determine the most severe level
                            has_severe = any(issue['严重程度'] == '严重' for issue in issues)
                            severity = '严重' if has_severe else '一般'
                            
                            # Format issues nicely
                            if len(issues) == 1:
                                # Single issue, use original format
                                combined_description = issues[0]['问题描述']
                                combined_suggestion = issues[0]['修改意见']
                            else:
                                # Multiple issues, use structured format
                                formatted_parts = []
                                for i, issue in enumerate(issues, 1):
                                    part = f"问题{i}：{issue['严重程度']}\n问题描述：{issue['问题描述']}\n修改意见：{issue['修改意见']}"
                                    formatted_parts.append(part)
                                
                                combined_description = '\n============\n'.join(formatted_parts)
                                combined_suggestion = f"共{len(issues)}个问题需要处理，请查看详细描述"
                            
                            scan_results.append({
                                '文件名': filename,
                                '行号': line_number,
                                '问题描述': combined_description,
                                '修改意见': combined_suggestion,
                                '严重程度': severity,
                                '问题数量': len(issues)  # Track how many issues were combined
                            })
                        
                        print(f"  Loaded {len(file_issues)} scan results grouped into {len(grouped_issues)} unique lines for {filename}")
                        
                except Exception as e:
                    print(f"  Error loading scan results from {json_file}: {e}")
                    continue
            
            print(f"Total scan results loaded: {len(scan_results)}")
                    
        except Exception as e:
            print(f"Error accessing scan results directory {self.scan_results_dir}: {e}")
        
        return scan_results
    
    def run_git_command(self, command):
        """
        Run a git command and return the output.
        
        Args:
            command (list): Git command as a list of arguments
            
        Returns:
            str: Command output
        """
        try:
            # add debug log to print the command
            print(f"Running git command: {' '.join(command)}")
            result = subprocess.run(
                ['git'] + command,
                cwd=self.repo_path,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error running git command: {e}")
            print(f"Error output: {e.stderr}")
            sys.exit(1)
    
    def get_commit_info(self, commit_hash):
        """
        Get detailed information about a specific commit.
        
        Args:
            commit_hash (str): The commit hash to get information for
            
        Returns:
            dict: Commit information
        """
        # Get basic commit info
        format_str = '%H%n%an%n%ae%n%at%n%s%n%b'
        commit_data = self.run_git_command(['show', '--no-patch', f'--format={format_str}', commit_hash])
        
        lines = commit_data.split('\n')
        commit_timestamp = int(lines[3])
        commit_date = datetime.datetime.fromtimestamp(commit_timestamp)
        
        commit_info = {
            'hash': lines[0],
            'author_name': lines[1],
            'author_email': lines[2],
            'timestamp': commit_timestamp,
            'date': commit_date.strftime('%Y-%m-%d %H:%M:%S'),
            'subject': lines[4],
            'body': '\n'.join(lines[5:]) if len(lines) > 5 else '',
            'files_changed': [],
        }
        
        # Get parent commit hash
        parent_hash = self.run_git_command(['rev-parse', f'{commit_hash}^'])
        commit_info['parent_hash'] = parent_hash
        
        return commit_info
    
    def get_changed_files(self, commit_hash):
        """
        Get list of files changed in the commit.
        
        Args:
            commit_hash (str): The commit hash
            
        Returns:
            list: List of changed files with their status
        """
        files_data = self.run_git_command(['diff-tree', '--no-commit-id', '--name-status', '-r', commit_hash])
        
        files = []
        for line in files_data.split('\n'):
            if not line.strip():
                continue
                
            parts = line.split('\t')
            status = parts[0]
            filename = parts[1] if len(parts) > 1 else ""
            
            status_map = {
                'A': 'added',
                'M': 'modified',
                'D': 'deleted',
                'R': 'renamed',
                'C': 'copied',
            }
            
            status_text = status_map.get(status[0], 'unknown')
            
            files.append({
                'status': status_text,
                'filename': filename
            })
            
        return files
    
    def get_file_diff(self, commit_hash, filename):
        """
        Get the diff for a specific file in the commit.
        
        Args:
            commit_hash (str): The commit hash
            filename (str): The filename to get diff for
            
        Returns:
            str: The file diff
        """
        try:
            diff = self.run_git_command(['diff', f'{commit_hash}^', commit_hash, '--', filename])
            return diff
        except Exception as e:
            print(f"Error getting diff for {filename}: {e}")
            return ""
    
    def parse_diff_to_html(self, diff_text):
        """
        Parse git diff output to HTML with syntax highlighting.
        
        Args:
            diff_text (str): Git diff output
            
        Returns:
            str: HTML representation of the diff
        """
        if not diff_text:
            return "<div class='diff-empty'>No changes</div>"
            
        html_lines = []
        
        # Process the diff header
        lines = diff_text.split('\n')
        in_header = True
        header_lines = []
        
        # Track line numbers
        old_line_num = 0
        new_line_num = 0
        
        for i, line in enumerate(lines):
            if in_header and line.startswith('@@'):
                in_header = False
                # Parse the hunk header to get starting line numbers
                match = re.match(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                if match:
                    old_line_num = int(match.group(1))
                    new_line_num = int(match.group(3))
                
                # Add header
                if header_lines:
                    html_lines.append("<div class='diff-header'>")
                    for header_line in header_lines:
                        html_lines.append(f"<div>{html.escape(header_line)}</div>")
                    html_lines.append("</div>")
                
                # Start diff content
                html_lines.append("<div class='diff-content'>")
                html_lines.append("<table class='diff-table'>")
            
            if in_header:
                header_lines.append(line)
                continue
                
            # Process diff content
            if line.startswith('@@'):
                # Diff hunk header
                html_lines.append("<tr class='diff-hunk-header'>")
                html_lines.append(f"<td colspan='4'>{html.escape(line)}</td>")
                html_lines.append("</tr>")
            elif line.startswith('+'):
                # Added line
                html_lines.append("<tr class='diff-added'>")
                html_lines.append("<td class='diff-sign'>+</td>")
                html_lines.append("<td class='diff-line-num'></td>")
                html_lines.append(f"<td class='diff-line-num'>{new_line_num}</td>")
                html_lines.append(f"<td class='diff-line-content'>{html.escape(line[1:])}</td>")
                html_lines.append("</tr>")
                new_line_num += 1
            elif line.startswith('-'):
                # Removed line
                html_lines.append("<tr class='diff-removed'>")
                html_lines.append("<td class='diff-sign'>-</td>")
                html_lines.append(f"<td class='diff-line-num'>{old_line_num}</td>")
                html_lines.append("<td class='diff-line-num'></td>")
                html_lines.append(f"<td class='diff-line-content'>{html.escape(line[1:])}</td>")
                html_lines.append("</tr>")
            elif line.startswith(' '):
                # Context line
                html_lines.append("<tr class='diff-context'>")
                html_lines.append("<td class='diff-sign'>&nbsp;</td>")
                html_lines.append(f"<td class='diff-line-num'>{old_line_num}</td>")
                html_lines.append(f"<td class='diff-line-num'>{new_line_num}</td>")
                html_lines.append(f"<td class='diff-line-content'>{html.escape(line[1:])}</td>")
                html_lines.append("</tr>")
                old_line_num += 1
                new_line_num += 1
            else:
                # Other lines
                html_lines.append("<tr>")
                html_lines.append("<td class='diff-sign'>&nbsp;</td>")
                html_lines.append("<td class='diff-line-num'></td>")
                html_lines.append("<td class='diff-line-num'></td>")
                html_lines.append(f"<td class='diff-line-content'>{html.escape(line)}</td>")
                html_lines.append("</tr>")
        
        if not in_header:
            html_lines.append("</table>")
            html_lines.append("</div>")
        
        return "\n".join(html_lines)
    

    


    
    def generate_review_page(self, commit_hash):
        """
        Generate a review page for a specific commit.
        
        Args:
            commit_hash (str): The commit hash to generate a review for
            
        Returns:
            str: Path to the generated HTML file
        """
        # Get commit information
        commit_info = self.get_commit_info(commit_hash)
        
        # Get changed files
        commit_info['files_changed'] = self.get_changed_files(commit_hash)
        
        # Generate CSS and JS
        self.renderer.generate_css()
        self.renderer.generate_js()
        
        # Build file tree
        file_tree = self.renderer._build_file_tree(commit_info['files_changed'])
        # Preload new file contents for dynamic context
        new_file_contents = {}
        for file_info in commit_info['files_changed']:
            filename = file_info['filename']
            try:
                with open(os.path.join(self.repo_path, filename), 'r', encoding='utf-8', errors='replace') as f:
                    new_file_contents[filename] = f.read().splitlines()
            except Exception:
                new_file_contents[filename] = []

        # Load scan results from directory
        scan_results = self.load_scan_results()

        # Generate HTML
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Review: {commit_info['subject']}</title>
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <div class="header">
        <h1>{html.escape(commit_info['subject'])}</h1>
        <div class="commit-info">
            <div class="commit-info-item">
                <div class="commit-info-label">Author</div>
                <div>{html.escape(commit_info['author_name'])} &lt;{html.escape(commit_info['author_email'])}&gt;</div>
            </div>
            <div class="commit-info-item">
                <div class="commit-info-label">Commit</div>
                <div>{commit_info['hash']}</div>
            </div>
            <div class="commit-info-item">
                <div class="commit-info-label">Date</div>
                <div>{commit_info['date']}</div>
            </div>
        </div>
        <div class="commit-message">{html.escape(commit_info['body'])}</div>
    </div>
    <div class="review-main">
        <div class="file-list-panel">
            <input type="text" class="file-search-box" placeholder="Search files..." />
            <div class="file-list file-tree-container">
                {self.renderer._render_file_tree(file_tree)}
            </div>
        </div>
        <div class="scan-results-panel">
            {self.renderer.render_scan_results_panel(scan_results)}
        </div>
        <div class="diff-panel">
'''
        # Add all diffs (all visible, each with anchor)
        for i, file_info in enumerate(commit_info['files_changed']):
            filename = file_info['filename']
            diff_text = self.get_file_diff(commit_hash, filename)
            diff_html, hunk_meta = self.renderer.parse_diff_to_html_with_expand(diff_text, filename, i, scan_results, self.repo_path)
            html_content += f'''
            <div id="diff-{i}" class="diff-container">
                <div class="diff-header">
                    <div>{html.escape(filename)}</div>
                </div>
                {diff_html}
            </div>
'''
        # Embed new file contents as JSON for JS
        html_content += f'''<script id="new-file-contents" type="application/json">{json.dumps(new_file_contents)}</script>'''
        html_content += '''
        </div>
    </div>
    <div class="footer">
        Generated by Git Commit Review Generator
    </div>
    <script src="assets/script.js"></script>
</body>
</html>
'''
        # Write HTML to file
        output_file = os.path.join(self.output_dir, f"review-{commit_hash[:7]}.html")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return output_file
    


    
    def generate_index_page(self, commit_hashes):
        """
        Generate an index page listing all commits.
        
        Args:
            commit_hashes (list): List of commit hashes
            
        Returns:
            str: Path to the generated index HTML file
        """
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Git Commit Reviews</title>
    <link rel="stylesheet" href="assets/style.css">
    <style>
        .commit-list {
            background-color: #fff;
            border: 1px solid #e1e4e8;
            border-radius: 3px;
            margin-bottom: 20px;
        }
        
        .commit-item {
            padding: 16px;
            border-bottom: 1px solid #e1e4e8;
        }
        
        .commit-item:last-child {
            border-bottom: none;
        }
        
        .commit-title {
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        .commit-meta {
            color: #586069;
            font-size: 12px;
            display: flex;
            flex-wrap: wrap;
        }
        
        .commit-meta-item {
            margin-right: 16px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Git Commit Reviews</h1>
    </div>
    
    <div class="commit-list">
"""
        
        for commit_hash in commit_hashes:
            commit_info = self.get_commit_info(commit_hash)
            
            html_content += f"""
        <div class="commit-item">
            <div class="commit-title">
                <a href="review-{commit_hash[:7]}.html">{html.escape(commit_info['subject'])}</a>
            </div>
            <div class="commit-meta">
                <div class="commit-meta-item">
                    <strong>Author:</strong> {html.escape(commit_info['author_name'])}
                </div>
                <div class="commit-meta-item">
                    <strong>Date:</strong> {commit_info['date']}
                </div>
                <div class="commit-meta-item">
                    <strong>Commit:</strong> {commit_hash[:7]}
                </div>
            </div>
        </div>
"""
        
        html_content += """
    </div>
    
    <div class="footer">
        Generated by Git Commit Review Generator
    </div>
</body>
</html>
"""
        
        # Write HTML to file
        output_file = os.path.join(self.output_dir, "index.html")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        return output_file
    
    def generate(self, num_commits=10):
        """
        Generate review pages for the most recent commits.
        
        Args:
            num_commits (int): Number of recent commits to generate reviews for
            
        Returns:
            list: Paths to the generated HTML files
        """
        # Get recent commits
        if self.commit_hash:
            commit_hashes = [self.commit_hash]
        else:
            commits_output = self.run_git_command(['log', f'-{num_commits}', '--pretty=format:%H'])
            commit_hashes = commits_output.split('\n')
        
        generated_files = []
        
        # Generate review page for each commit
        for commit_hash in commit_hashes:
            output_file = self.generate_review_page(commit_hash)
            generated_files.append(output_file)
            print(f"Generated review page for commit {commit_hash[:7]}: {output_file}")
        
        # Generate index page
        index_file = self.generate_index_page(commit_hashes)
        generated_files.append(index_file)
        print(f"Generated index page: {index_file}")
        
        return generated_files


def main():
    """Main function to parse arguments and run the generator."""
    parser = argparse.ArgumentParser(description='Generate static HTML pages for Git/SVN commit/revision reviews')
    parser.add_argument('repo_path', help='Path to the Git repository or SVN working copy')
    parser.add_argument('--output-dir', '-o', default='./reviews', help='Output directory for generated HTML files')
    parser.add_argument('--commit', '-c', help='Specific commit hash (Git) or revision number (SVN) to generate review for')
    parser.add_argument('--num-commits', '-n', type=int, default=1, help='Number of recent commits/revisions to generate reviews for')
    parser.add_argument('--template-dir', '-t', help='Directory containing custom templates')
    parser.add_argument('--scan-results', '-s', help='Directory containing scan results JSON files')
    
    args = parser.parse_args()
    
    try:
        # Detect repository type
        repo_type = is_git_or_svn(args.repo_path)
        
        if repo_type == 'git':
            print(f"Detected Git repository at {args.repo_path}")
            generator = GitCommitReviewGenerator(
                args.repo_path,
                args.output_dir,
                args.commit,
                args.template_dir,
                args.scan_results
            )
            generator.generate(args.num_commits)
            
        elif repo_type == 'svn':
            print(f"Detected SVN repository at {args.repo_path}")
            # Import SVN generator
            from svn_review_generator import SVNRevisionReviewGenerator
            generator = SVNRevisionReviewGenerator(
                args.repo_path,
                args.output_dir,
                args.commit,  # This will be treated as revision number for SVN
                args.template_dir,
                args.scan_results
            )
            generator.generate(args.num_commits)
            
        else:
            print(f"Error: Unable to detect repository type at {args.repo_path}")
            print("Please ensure the path points to a valid Git repository or SVN working copy")
            sys.exit(1)
        
        print(f"\nReview pages generated successfully in {args.output_dir}")
        print(f"Open {os.path.join(args.output_dir, 'index.html')} in your browser to view the reviews")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()