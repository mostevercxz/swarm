#!/usr/bin/env python3
"""
SVN Revision Review Page Generator

This script generates a static HTML page similar to Helix Swarm's review page,
but based on SVN revisions. It extracts revision information from an SVN repository
and creates a visually similar review page.
"""

import os
import sys
import subprocess
import datetime
import re
import html
import json
from xml.etree import ElementTree as ET


class SVNRevisionReviewGenerator:
    """
    A class to generate a static HTML page for SVN revision reviews
    similar to Helix Swarm's review page.
    """
    
    def __init__(self, repo_path, output_dir, revision=None, template_dir=None, scan_results_dir=None):
        """
        Initialize the generator with repository path and output directory.
        
        Args:
            repo_path (str): Path to the SVN working copy
            output_dir (str): Directory to output the generated HTML files
            revision (str, optional): Specific revision number to generate review for
            template_dir (str, optional): Directory containing custom templates
            scan_results_dir (str, optional): Directory containing scan results JSON files
        """
        self.repo_path = os.path.abspath(repo_path)
        self.output_dir = os.path.abspath(output_dir)
        self.revision = revision
        self.template_dir = template_dir
        self.scan_results_dir = scan_results_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create assets directory
        self.assets_dir = os.path.join(self.output_dir, 'assets')
        os.makedirs(self.assets_dir, exist_ok=True)
        
        # Verify SVN working copy
        try:
            self.run_svn_command(['info'])
        except Exception:
            raise ValueError(f"Not a valid SVN working copy: {self.repo_path}")
    
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
    
    def run_svn_command(self, command):
        """
        Run an SVN command and return the output.
        
        Args:
            command (list): SVN command as a list of arguments
            
        Returns:
            str: Command output
        """
        try:
            print(f"Running svn command: {' '.join(command)}")
            result = subprocess.run(
                ['svn'] + command,
                cwd=self.repo_path,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error running svn command: {e}")
            print(f"Error output: {e.stderr}")
            sys.exit(1)
    
    def get_revision_info(self, revision):
        """
        Get detailed information about a specific revision.
        
        Args:
            revision (str): The revision number to get information for
            
        Returns:
            dict: Revision information
        """
        # Get revision info using svn log with XML output
        log_output = self.run_svn_command(['log', f'-r{revision}', '--xml', '-v'])
        
        # Parse XML
        try:
            root = ET.fromstring(log_output)
            logentry = root.find('logentry')
            
            if logentry is None:
                raise ValueError(f"No log entry found for revision {revision}")
            
            # Extract basic info
            revision_num = logentry.get('revision')
            author = logentry.find('author').text if logentry.find('author') is not None else 'Unknown'
            date_text = logentry.find('date').text if logentry.find('date') is not None else ''
            msg = logentry.find('msg').text if logentry.find('msg') is not None else ''
            
            # Parse date
            if date_text:
                # SVN date format: 2023-01-01T12:00:00.000000Z
                date_obj = datetime.datetime.strptime(date_text[:19], '%Y-%m-%dT%H:%M:%S')
                formatted_date = date_obj.strftime('%Y-%m-%d %H:%M:%S')
                timestamp = int(date_obj.timestamp())
            else:
                formatted_date = 'Unknown'
                timestamp = 0
            
            revision_info = {
                'revision': revision_num,
                'author_name': author,
                'author_email': f'{author}@company.com',  # SVN doesn't store email
                'timestamp': timestamp,
                'date': formatted_date,
                'subject': msg.split('\n')[0] if msg else f'Revision {revision_num}',
                'body': msg,
                'files_changed': [],
            }
            
            return revision_info
            
        except ET.ParseError as e:
            print(f"Error parsing SVN log XML: {e}")
            sys.exit(1)
    
    def get_changed_files(self, revision):
        """
        Get list of files changed in the revision.
        
        Args:
            revision (str): The revision number
            
        Returns:
            list: List of changed files with their status
        """
        # Get changed files using svn log with verbose flag
        log_output = self.run_svn_command(['log', f'-r{revision}', '--xml', '-v'])
        
        try:
            root = ET.fromstring(log_output)
            logentry = root.find('logentry')
            
            if logentry is None:
                return []
            
            files = []
            paths = logentry.find('paths')
            if paths is not None:
                for path in paths.findall('path'):
                    action = path.get('action')
                    filename = path.text
                    
                    # Remove leading slash and trunk/branches/tags prefix
                    if filename.startswith('/'):
                        filename = filename[1:]
                    
                    # Common SVN path prefixes to remove
                    for prefix in ['trunk/', 'branches/main/', 'branches/master/']:
                        if filename.startswith(prefix):
                            filename = filename[len(prefix):]
                            break
                    
                    action_map = {
                        'A': 'added',
                        'M': 'modified',
                        'D': 'deleted',
                        'R': 'renamed',
                    }
                    
                    status_text = action_map.get(action, 'unknown')
                    
                    files.append({
                        'status': status_text,
                        'filename': filename
                    })
            
            return files
            
        except ET.ParseError as e:
            print(f"Error parsing SVN log XML: {e}")
            return []
    
    def get_file_diff(self, revision, filename):
        """
        Get the diff for a specific file in the revision.
        
        Args:
            revision (str): The revision number
            filename (str): The filename to get diff for
            
        Returns:
            str: The file diff
        """
        try:
            # For SVN, we need to construct the full path
            # First, let's get the repository root
            info_output = self.run_svn_command(['info', '--xml'])
            info_root = ET.fromstring(info_output)
            repo_root = info_root.find('.//repository/root').text
            working_copy_root = info_root.find('.//wcroot-abspath').text
            
            # Construct the URL for the file
            file_url = f"{repo_root}/trunk/{filename}"
            
            # Get diff between revision-1 and revision
            prev_revision = str(int(revision) - 1)
            diff = self.run_svn_command(['diff', f'-r{prev_revision}:{revision}', file_url])
            return diff
        except Exception as e:
            print(f"Error getting diff for {filename}: {e}")
            return ""
    
    # The rest of the methods (parse_diff_to_html, generate_css, generate_js, etc.) 
    # can be copied from GitCommitReviewGenerator with minimal modifications
    # since they mostly work with the data structures we've created above
    
    def _build_file_tree(self, files_changed):
        """
        Build a nested dictionary representing the folder/file tree from a flat file list.
        """
        tree = {}
        for idx, file_info in enumerate(files_changed):
            parts = file_info['filename'].split('/')
            node = tree
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = {'__file__': file_info, '__index__': idx}
        return tree

    def _render_file_tree(self, tree, parent_path="", level=0):
        """
        Recursively render the file tree as nested <ul>/<li> HTML.
        """
        html_out = '<ul class="file-tree' + (" root" if level == 0 else "") + '">'
        for name, value in sorted(tree.items()):
            if isinstance(value, dict) and '__file__' in value:
                file_info = value['__file__']
                idx = value['__index__']
                status_class = file_info['status']
                status_text = file_info['status'].capitalize()
                base_name = os.path.basename(file_info["filename"])
                html_out += f'<li class="file-leaf"><div class="file-item" data-diff-id="diff-{idx}"><span class="file-status {status_class}">{status_text}</span><span class="file-name">{html.escape(base_name)}</span></div></li>'
            else:
                folder_id = f"folder-{parent_path.replace('/', '-')}-{name}".replace(' ', '-')
                html_out += f'<li class="file-folder" data-folder="{html.escape(name)}"><div class="folder-label" data-folder-id="{folder_id}"><span class="folder-caret">▶</span><span class="folder-name">{html.escape(name)}</span></div>'
                html_out += self._render_file_tree(value, parent_path + name + '/', level+1)
                html_out += '</li>'
        html_out += '</ul>'
        return html_out
    
    def generate(self, num_revisions=10):
        """
        Generate review pages for the most recent revisions.
        
        Args:
            num_revisions (int): Number of recent revisions to generate reviews for
            
        Returns:
            list: Paths to the generated HTML files
        """
        # Get recent revisions
        if self.revision:
            revisions = [self.revision]
        else:
            # Get recent revisions using svn log
            log_output = self.run_svn_command(['log', f'-l{num_revisions}', '--xml'])
            root = ET.fromstring(log_output)
            revisions = [entry.get('revision') for entry in root.findall('logentry')]
        
        generated_files = []
        
        # Generate review page for each revision
        for revision in revisions:
            output_file = self.generate_review_page(revision)
            generated_files.append(output_file)
            print(f"Generated review page for revision {revision}: {output_file}")
        
        # Generate index page
        index_file = self.generate_index_page(revisions)
        generated_files.append(index_file)
        print(f"Generated index page: {index_file}")
        
        return generated_files
    
    def parse_diff_to_html(self, diff_text):
        """
        Parse SVN diff output to HTML with syntax highlighting.
        
        Args:
            diff_text (str): SVN diff output
            
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
    
    def generate_css(self):
        """Generate CSS for the review page."""
        # Copy CSS from Git generator with minor adaptations
        css_content = """
        /* Reset and base styles */
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
        }
        a {
            color: #0366d6;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        .header {
            background-color: #fff;
            border: 1px solid #e1e4e8;
            border-radius: 3px;
            padding: 16px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .header h1 {
            font-size: 24px;
            margin-bottom: 8px;
        }
        .revision-info {
            display: flex;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }
        .revision-info-item {
            margin-right: 24px;
            margin-bottom: 8px;
        }
        .revision-info-label {
            font-weight: 600;
            color: #586069;
        }
        .revision-message {
            background-color: #f6f8fa;
            border: 1px solid #e1e4e8;
            border-radius: 3px;
            padding: 16px;
            margin-top: 16px;
            white-space: pre-wrap;
        }
        /* Main review layout */
        .review-main {
            display: flex;
            flex-direction: row;
            gap: 24px;
            min-height: 400px;
        }
        .file-list-panel {
            width: 320px;
            min-width: 220px;
            max-width: 400px;
            position: sticky;
            top: 0;
            align-self: flex-start;
            z-index: 2;
            background: #f5f5f5;
        }
        .scan-results-panel {
            width: 20%;
            min-width: 200px;
            position: sticky;
            top: 0;
            align-self: flex-start;
            z-index: 2;
            background: #f5f5f5;
            padding: 0 10px;
        }
        .scan-results-list {
            background-color: #fff;
            border: 1px solid #e1e4e8;
            border-radius: 3px;
            margin-bottom: 20px;
        }
        .scan-result-item {
            padding: 8px;
            border-bottom: 1px solid #e1e4e8;
            font-size: 12px;
            cursor: pointer;
        }
        .scan-result-item:last-child {
            border-bottom: none;
        }
        .scan-result-item.severe {
            background-color: #ffebee;
        }
        .scan-result-item .line-number {
            color: #586069;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .scan-result-item .description {
            margin-bottom: 4px;
        }
        .scan-result-item .suggestion {
            color: #586069;
            font-style: italic;
        }
        .file-list {
            background-color: #fff;
            border: 1px solid #e1e4e8;
            border-radius: 3px;
            margin-bottom: 20px;
        }
        .file-item {
            padding: 8px 16px;
            border-bottom: 1px solid #e1e4e8;
            display: flex;
            align-items: center;
            cursor: pointer;
        }
        .file-item:last-child {
            border-bottom: none;
        }
        .file-item.active {
            background-color: #f1f8ff;
        }
        .file-status {
            margin-right: 8px;
            font-weight: 600;
        }
        .file-status.added {
            color: #28a745;
        }
        .file-status.modified {
            color: #0366d6;
        }
        .file-status.deleted {
            color: #d73a49;
        }
        .diff-panel {
            flex: 1 1 0%;
            min-width: 0;
        }
        .diff-container {
            background-color: #fff;
            border: 1px solid #e1e4e8;
            border-radius: 3px;
            margin-bottom: 20px;
            overflow: hidden;
        }
        .diff-header {
            background-color: #f6f8fa;
            padding: 8px 16px;
            border-bottom: 1px solid #e1e4e8;
            font-family: 'JetBrains Mono', 'Menlo', 'Monaco', 'Courier New', monospace;
            font-size: 12px;
            color: #586069;
        }
        .diff-content {
            overflow-x: auto;
        }
        .diff-table {
            width: 100%;
            border-collapse: collapse;
            font-family: 'JetBrains Mono', 'Menlo', 'Monaco', 'Courier New', monospace;
            font-size: 12px;
            tab-size: 4;
        }
        .diff-table tr {
            height: 20px;
        }
        .diff-hunk-header {
            background-color: #f1f8ff;
            color: #586069;
        }
        .diff-sign {
            width: 1%;
            padding: 0 8px;
            text-align: center;
            user-select: none;
        }
        .diff-line-num {
            width: 1%;
            padding: 0 8px;
            text-align: right;
            color: #586069;
            user-select: none;
            border-right: 1px solid #e1e4e8;
        }
        .diff-line-content {
            padding: 0 8px;
            white-space: pre;
        }
        .diff-added {
            background-color: rgba(40, 167, 69, 0.15);
        }
        .diff-added .diff-sign {
            background-color: rgba(40, 167, 69, 0.2);
            color: #28a745;
        }
        .diff-removed {
            background-color: rgba(220, 53, 69, 0.15);
        }
        .diff-removed .diff-sign {
            background-color: rgba(220, 53, 69, 0.2);
            color: #d73a49;
        }
        .diff-context {
            background-color: #fff;
        }
        .diff-empty {
            padding: 16px;
            color: #586069;
            font-style: italic;
        }
        .footer {
            margin-top: 40px;
            text-align: center;
            color: #586069;
            font-size: 12px;
        }
        .file-search-box {
            width: 100%;
            padding: 8px 12px;
            margin-bottom: 8px;
            border: 1px solid #e1e4e8;
            border-radius: 3px;
            font-size: 14px;
        }
        .file-tree {
            list-style: none;
            padding-left: 0;
        }
        .file-tree .file-folder > .folder-label {
            cursor: pointer;
            font-weight: 600;
            padding: 6px 16px;
            display: flex;
            align-items: center;
        }
        .file-tree .file-folder > .folder-label .folder-caret {
            display: inline-block;
            width: 1em;
            margin-right: 4px;
            transition: transform 0.2s;
        }
        .file-tree .file-folder.collapsed > ul {
            display: none;
        }
        .file-tree .file-folder.collapsed > .folder-label .folder-caret {
            transform: rotate(0deg);
        }
        .file-tree .file-folder > .folder-label .folder-caret {
            transform: rotate(90deg);
        }
        .file-tree .file-leaf .file-item {
            padding-left: 32px;
        }
        .file-tree .file-leaf .file-item.active {
            background-color: #f1f8ff;
        }
        .file-tree .file-leaf .file-status {
            margin-right: 8px;
        }
        .file-tree .file-leaf .file-name {
            word-break: break-all;
        }
        .file-tree .file-folder {
            margin-bottom: 0;
        }
        .file-tree .file-folder > ul {
            margin-left: 1em;
            border-left: 1px dotted #e1e4e8;
            padding-left: 0.5em;
        }
        """
        
        css_path = os.path.join(self.assets_dir, 'style.css')
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(css_content)
        return css_path
    
    def generate_js(self):
        """Generate JavaScript for the review page."""
        js_content = """
        document.addEventListener('DOMContentLoaded', function() {
            // Folder expand/collapse
            document.querySelectorAll('.folder-label').forEach(function(label) {
                label.addEventListener('click', function() {
                    var li = label.parentElement;
                    li.classList.toggle('collapsed');
                });
            });
            
            // File list click to scroll to diff
            const fileItems = document.querySelectorAll('.file-item');
            fileItems.forEach(item => {
                item.addEventListener('click', () => {
                    fileItems.forEach(i => i.classList.remove('active'));
                    item.classList.add('active');
                    const diffId = item.getAttribute('data-diff-id');
                    const diffElem = document.getElementById(diffId);
                    if (diffElem) {
                        diffElem.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                });
            });
            
            // Scan result panel click to jump to code line
            document.querySelectorAll('.scan-result-item[data-jump]').forEach(function(item) {
                item.addEventListener('click', function() {
                    const jumpId = item.getAttribute('data-jump');
                    const codeElem = document.getElementById(jumpId);
                    if (codeElem) {
                        codeElem.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        codeElem.classList.add('scan-result-highlight');
                        setTimeout(() => codeElem.classList.remove('scan-result-highlight'), 1600);
                    }
                });
            });
            
            // File search filter
            const searchBox = document.querySelector('.file-search-box');
            if (searchBox) {
                searchBox.addEventListener('input', function() {
                    const query = searchBox.value.toLowerCase();
                    document.querySelectorAll('.file-tree .file-leaf').forEach(function(leaf) {
                        const name = leaf.textContent.toLowerCase();
                        leaf.style.display = name.includes(query) ? '' : 'none';
                    });
                    // Hide folders with no visible children
                    document.querySelectorAll('.file-tree .file-folder').forEach(function(folder) {
                        const anyVisible = Array.from(folder.querySelectorAll(':scope > ul > .file-leaf, :scope > ul > .file-folder')).some(function(child) {
                            return child.style.display !== 'none';
                        });
                        folder.style.display = anyVisible ? '' : 'none';
                    });
                });
            }
        });
        """
        
        js_path = os.path.join(self.assets_dir, 'script.js')
        with open(js_path, 'w', encoding='utf-8') as f:
            f.write(js_content)
        return js_path
    
    def generate_review_page(self, revision):
        """
        Generate a review page for a specific revision.
        
        Args:
            revision (str): The revision number to generate a review for
            
        Returns:
            str: Path to the generated HTML file
        """
        # Get revision information
        revision_info = self.get_revision_info(revision)
        
        # Get changed files
        revision_info['files_changed'] = self.get_changed_files(revision)
        
        # Generate CSS and JS
        self.generate_css()
        self.generate_js()
        
        # Build file tree
        file_tree = self._build_file_tree(revision_info['files_changed'])
        
        # Load scan results
        scan_results = self.load_scan_results()

        # Generate HTML
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Review: {revision_info['subject']}</title>
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <div class="header">
        <h1>{html.escape(revision_info['subject'])}</h1>
        <div class="revision-info">
            <div class="revision-info-item">
                <div class="revision-info-label">Author</div>
                <div>{html.escape(revision_info['author_name'])} &lt;{html.escape(revision_info['author_email'])}&gt;</div>
            </div>
            <div class="revision-info-item">
                <div class="revision-info-label">Revision</div>
                <div>{revision_info['revision']}</div>
            </div>
            <div class="revision-info-item">
                <div class="revision-info-label">Date</div>
                <div>{revision_info['date']}</div>
            </div>
        </div>
        <div class="revision-message">{html.escape(revision_info['body'])}</div>
    </div>
    <div class="review-main">
        <div class="file-list-panel">
            <input type="text" class="file-search-box" placeholder="Search files..." />
            <div class="file-list file-tree-container">
                {self._render_file_tree(file_tree)}
            </div>
        </div>
        <div class="scan-results-panel">
            <div class="scan-results-list">
'''
        
        # Add scan results to the panel
        for result in scan_results:
            severity_class = 'severe' if result['严重程度'] == '严重' else ''
            safe_filename = result['文件名'].replace('/', '-').replace('\\', '-').replace('.', '-')
            jump_id = f"scanresult-{safe_filename}-{result['行号']}"
            issue_count = result.get('问题数量', 1)
            count_text = f" ({issue_count} issues)" if issue_count > 1 else ""
            html_content += f'''
                <div class="scan-result-item {severity_class}" data-line="{result['行号']}" data-jump="{jump_id}">
                    <div class="file-name">文件名：{html.escape(result['文件名'])}</div>
                    <div class="line-number">行号： {result['行号']}{count_text}</div>
                    <div class="description">{html.escape(result['问题描述'])}</div>
                    <div class="suggestion">{html.escape(result['修改意见'])}</div>
                </div>
'''
        html_content += '''
            </div>
        </div>
        <div class="diff-panel">
'''
        # Add all diffs
        for i, file_info in enumerate(revision_info['files_changed']):
            filename = file_info['filename']
            diff_text = self.get_file_diff(revision, filename)
            diff_html = self.parse_diff_to_html(diff_text)
            html_content += f'''
            <div id="diff-{i}" class="diff-container">
                <div class="diff-header">
                    <div>{html.escape(filename)}</div>
                </div>
                {diff_html}
            </div>
'''
        
        html_content += '''
        </div>
    </div>
    <div class="footer">
        Generated by SVN Revision Review Generator
    </div>
    <script src="assets/script.js"></script>
</body>
</html>
'''
        
        # Write HTML to file
        output_file = os.path.join(self.output_dir, f"review-r{revision}.html")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return output_file
    
    def generate_index_page(self, revisions):
        """
        Generate an index page listing all revisions.
        
        Args:
            revisions (list): List of revision numbers
            
        Returns:
            str: Path to the generated index HTML file
        """
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SVN Revision Reviews</title>
    <link rel="stylesheet" href="assets/style.css">
    <style>
        .revision-list {
            background-color: #fff;
            border: 1px solid #e1e4e8;
            border-radius: 3px;
            margin-bottom: 20px;
        }
        
        .revision-item {
            padding: 16px;
            border-bottom: 1px solid #e1e4e8;
        }
        
        .revision-item:last-child {
            border-bottom: none;
        }
        
        .revision-title {
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        .revision-meta {
            color: #586069;
            font-size: 12px;
            display: flex;
            flex-wrap: wrap;
        }
        
        .revision-meta-item {
            margin-right: 16px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>SVN Revision Reviews</h1>
    </div>
    
    <div class="revision-list">
"""
        
        for revision in revisions:
            revision_info = self.get_revision_info(revision)
            
            html_content += f"""
        <div class="revision-item">
            <div class="revision-title">
                <a href="review-r{revision}.html">{html.escape(revision_info['subject'])}</a>
            </div>
            <div class="revision-meta">
                <div class="revision-meta-item">
                    <strong>Author:</strong> {html.escape(revision_info['author_name'])}
                </div>
                <div class="revision-meta-item">
                    <strong>Date:</strong> {revision_info['date']}
                </div>
                <div class="revision-meta-item">
                    <strong>Revision:</strong> r{revision}
                </div>
            </div>
        </div>
"""
        
        html_content += """
    </div>
    
    <div class="footer">
        Generated by SVN Revision Review Generator
    </div>
</body>
</html>
"""
        
        # Write HTML to file
        output_file = os.path.join(self.output_dir, "index.html")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        return output_file 