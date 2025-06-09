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
from render import Render


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
        
        # Initialize renderer
        self.renderer = Render(self.output_dir, self.assets_dir)
        
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
        if not self.scan_results_dir:
            return []
            
        if not os.path.isdir(self.scan_results_dir):
            print(f"Warning: Scan results directory does not exist: {self.scan_results_dir}")
            return []
        
        try:
            # Find all JSON files in the directory
            json_files = []
            for filename in os.listdir(self.scan_results_dir):
                if filename.lower().endswith('.json'):
                    json_files.append(os.path.join(self.scan_results_dir, filename))
            
            print(f"Found {len(json_files)} JSON files in scan results directory")
            
            # Collect all issues from all JSON files first
            from collections import defaultdict
            all_issues_by_file_line = defaultdict(list)
            
            # Helper function to clean text content
            def clean_text_content(text):
                if not text:
                    return text
                # Remove navigation elements like "向上10行", "向下10行", etc.
                import re
                # Remove navigation patterns
                text = re.sub(r'向[上下]\d+行', '', text)
                # Remove problematic navigation elements but keep normal text
                # Just clean up multiple spaces and newlines for now
                text = re.sub(r'\s+', ' ', text).strip()
                return text
            
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
                        
                        # Collect all issues for this file
                        file_issues = []
                        
                        # Process "可能存在的问题" (general severity)
                        if '可能存在的问题' in file_data:
                            for issue in file_data['可能存在的问题']:
                                line_range = issue.get('行号范围', '1')
                                line_number = parse_line_number(line_range, source_code)
                                
                                # Clean the text content
                                description = clean_text_content(issue.get('问题描述', ''))
                                suggestion = clean_text_content(issue.get('修改意见', ''))
                                
                                file_issues.append({
                                    '文件名': filename,
                                    '行号': line_number,
                                    '问题描述': description,
                                    '修改意见': suggestion,
                                    '严重程度': '一般'
                                })
                        
                        # Process "肯定存在的问题" (severe)
                        if '肯定存在的问题' in file_data:
                            for issue in file_data['肯定存在的问题']:
                                line_range = issue.get('行号范围', '1')
                                line_number = parse_line_number(line_range, source_code)
                                
                                # Clean the text content
                                description = clean_text_content(issue.get('问题描述', ''))
                                suggestion = clean_text_content(issue.get('修改意见', ''))
                                
                                file_issues.append({
                                    '文件名': filename,
                                    '行号': line_number,
                                    '问题描述': description,
                                    '修改意见': suggestion,
                                    '严重程度': '严重'
                                })
                        
                        # Add all issues to the global collection, keyed by (filename, line_number)
                        for issue in file_issues:
                            key = (issue['文件名'], issue['行号'])
                            all_issues_by_file_line[key].append(issue)
                        
                        print(f"  Loaded {len(file_issues)} scan results for {filename}")
                        
                except Exception as e:
                    print(f"  Error loading scan results from {json_file}: {e}")
                    continue
            
            # Now create the final scan results by grouping all issues by file and line
            scan_results = []
            for (filename, line_number), issues in all_issues_by_file_line.items():
                print(f"  DEBUG: Processing {filename} line {line_number} with {len(issues)} issues:")
                for i, issue in enumerate(issues):
                    print(f"    Issue {i+1}: {issue['严重程度']} - {issue['问题描述'][:50]}...")
                
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
                
                final_result = {
                    '文件名': filename,
                    '行号': line_number,
                    '问题描述': combined_description,
                    '修改意见': combined_suggestion,
                    '严重程度': severity,
                    '问题数量': len(issues)  # Track how many issues were combined
                }
                scan_results.append(final_result)
                print(f"  DEBUG: Created final scan result for {filename}:{line_number} with {len(issues)} combined issues")
            
            # Print summary by file
            file_summary = defaultdict(list)
            for result in scan_results:
                file_summary[result['文件名']].append(result['行号'])
            
            for filename, line_numbers in file_summary.items():
                print(f"  Final results for {filename} on lines: {sorted(line_numbers)}")
            
            print(f"Total unique scan results loaded: {len(scan_results)}")
                    
        except Exception as e:
            print(f"Error accessing scan results directory {self.scan_results_dir}: {e}")
            return []
        
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
    
    def parse_diff_to_html(self, diff_text, filename="", scan_results=None):
        """
        Parse SVN diff output to HTML with syntax highlighting and scan result integration.
        
        Args:
            diff_text (str): SVN diff output
            filename (str): The filename being processed
            scan_results (list): List of scan results for this file
            
        Returns:
            str: HTML representation of the diff
        """
        if not diff_text:
            return "<div class='diff-empty'>No changes</div>"
        
        # Filter scan results for this file
        file_scan_results = {}
        if scan_results:
            print(f"  DEBUG: parse_diff_to_html processing {filename} with {len(scan_results)} total scan results")
            for result in scan_results:
                # Normalize filename for comparison
                result_filename = result['文件名'].replace('\\', '/')
                current_filename = filename.replace('\\', '/')
                
                # More flexible filename matching
                is_match = (
                    result_filename == current_filename or 
                    current_filename.endswith(result_filename) or
                    result_filename.endswith(current_filename) or
                    os.path.basename(result_filename) == os.path.basename(current_filename)
                )
                
                if is_match:
                    line_num = result['行号']
                    if line_num not in file_scan_results:
                        file_scan_results[line_num] = []
                    file_scan_results[line_num].append(result)
                    print(f"    DEBUG: Added scan result for line {line_num} (问题数量: {result.get('问题数量', 1)})")
            
            # Debug: print what scan results we found for this file
            if file_scan_results:
                print(f"  Found scan results for {filename} on lines: {sorted(file_scan_results.keys())}")
                for line_num, results in file_scan_results.items():
                    print(f"    Line {line_num}: {len(results)} scan result entries")
            else:
                print(f"  No scan results found for {filename}")
                # Print available scan result filenames for debugging
                available_files = set(result['文件名'] for result in scan_results)
                print(f"  Available scan result files: {list(available_files)}")
        
        # Use the shared method from render.py
        return self.renderer.parse_diff_to_html_with_expand(diff_text, filename, 0, file_scan_results, self.repo_path)


    
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
        self.renderer.generate_css()
        self.renderer.generate_js()
        
        # Build file tree
        file_tree = self.renderer._build_file_tree(revision_info['files_changed'])
        
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
                {self.renderer._render_file_tree(file_tree)}
            </div>
        </div>
        <div class="scan-results-panel">
            {self.renderer.render_scan_results_panel(scan_results)}
        </div>
        <div class="diff-panel">
'''
        # Add all diffs
        for i, file_info in enumerate(revision_info['files_changed']):
            filename = file_info['filename']
            diff_text = self.get_file_diff(revision, filename)
            diff_html = self.parse_diff_to_html(diff_text, filename, scan_results)
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