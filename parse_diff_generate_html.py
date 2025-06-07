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

class GitCommitReviewGenerator:
    """
    A class to generate a static HTML page for Git commit reviews
    similar to Helix Swarm's review page.
    """
    
    def __init__(self, repo_path, output_dir, commit_hash=None, template_dir=None):
        """
        Initialize the generator with repository path and output directory.
        
        Args:
            repo_path (str): Path to the Git repository
            output_dir (str): Directory to output the generated HTML files
            commit_hash (str, optional): Specific commit hash to generate review for
            template_dir (str, optional): Directory containing custom templates
        """
        self.repo_path = os.path.abspath(repo_path)
        self.output_dir = os.path.abspath(output_dir)
        self.commit_hash = commit_hash
        self.template_dir = template_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create assets directory
        self.assets_dir = os.path.join(self.output_dir, 'assets')
        os.makedirs(self.assets_dir, exist_ok=True)
        
        # Verify git repository
        if not os.path.isdir(os.path.join(self.repo_path, '.git')):
            raise ValueError(f"Not a valid Git repository: {self.repo_path}")
    
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
                text=True
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
    
    def generate_css(self):
        """
        Generate CSS for the review page.
        
        Returns:
            str: Path to the generated CSS file
        """
        css_content = """
        /* Reset and base styles */
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
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
        .commit-info {
            display: flex;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }
        .commit-info-item {
            margin-right: 24px;
            margin-bottom: 8px;
        }
        .commit-info-label {
            font-weight: 600;
            color: #586069;
        }
        .commit-message {
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
            font-family: SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 12px;
            color: #586069;
        }
        .diff-content {
            overflow-x: auto;
        }
        .diff-table {
            width: 100%;
            border-collapse: collapse;
            font-family: SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace;
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
            background-color: #e6ffec;
        }
        .diff-added .diff-sign {
            background-color: #ccffd8;
            color: #28a745;
        }
        .diff-removed {
            background-color: #ffebe9;
        }
        .diff-removed .diff-sign {
            background-color: #ffd7d5;
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
        """
        Generate JavaScript for the review page.
        
        Returns:
            str: Path to the generated JS file
        """
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
            // Expandable context logic
            const fileContents = JSON.parse(document.getElementById('new-file-contents').textContent);
            document.querySelectorAll('.expand-btn').forEach(function(btn) {
                btn.addEventListener('click', function() {
                    const tr = btn.closest('tr');
                    const table = btn.closest('table');
                    const filename = table.getAttribute('data-filename');
                    const lines = fileContents[filename] || [];
                    let insertIdx = Array.from(table.rows).indexOf(tr);
                    let expandType = btn.getAttribute('data-expand');
                    let contextLines = 10;
                    function lineAlreadyPresent(ln) {
                        return Array.from(table.querySelectorAll('.expanded-context .diff-line-num')).some(function(td) {
                            return parseInt(td.textContent) === ln;
                        });
                    }
                    if (expandType === 'above') {
                        // Find first visible line number in this hunk
                        let firstLineNum = null;
                        for (let i = insertIdx + 1; i < table.rows.length; ++i) {
                            let row = table.rows[i];
                            if (row.classList.contains('diff-context') || row.classList.contains('diff-added')) {
                                let num = row.querySelectorAll('.diff-line-num')[1];
                                if (num && num.textContent) {
                                    firstLineNum = parseInt(num.textContent);
                                    break;
                                }
                            }
                        }
                        if (firstLineNum === null) return;
                        // Find previous diff hunk header above this expand row
                        let prevHunkEndLine = 0;
                        for (let i = insertIdx - 1; i >= 0; --i) {
                            let row = table.rows[i];
                            if (row.classList.contains('diff-hunk-header')) {
                                // Find the last line number in the previous hunk
                                // Scan down from this header to the next hunk or end
                                for (let j = i + 1; j < table.rows.length; ++j) {
                                    let r = table.rows[j];
                                    if (r.classList.contains('diff-hunk-header')) break;
                                    if (r.classList.contains('diff-context') || r.classList.contains('diff-added')) {
                                        let num = r.querySelectorAll('.diff-line-num')[1];
                                        if (num && num.textContent) {
                                            let n = parseInt(num.textContent);
                                            if (!isNaN(n) && n > prevHunkEndLine) prevHunkEndLine = n;
                                        }
                                    }
                                }
                                break;
                            }
                        }
                        let start = Math.max(prevHunkEndLine + 1, firstLineNum - contextLines);
                        let end = firstLineNum;
                        let inserted = false;
                        for (let ln = start; ln < end; ++ln) {
                            if (lineAlreadyPresent(ln)) continue;
                            let content = lines[ln - 1] || '';
                            let newRow = document.createElement('tr');
                            newRow.className = 'diff-context expanded-context';
                            newRow.innerHTML = `<td class='diff-sign'>&nbsp;</td><td class='diff-line-num'></td><td class='diff-line-num'>${ln}</td><td class='diff-line-content'>${escapeHtml(content)}</td>`;
                            table.tBodies[0].insertBefore(newRow, tr);
                            inserted = true;
                        }
                        // Hide the button if we reached the top or next would overlap with previous diff
                        if (start === prevHunkEndLine + 1 || !inserted) {
                            btn.style.display = 'none';
                        } else {
                            // Check if next batch would overlap
                            let nextStart = Math.max(prevHunkEndLine + 1, start - contextLines);
                            let overlap = false;
                            for (let ln = nextStart; ln < start; ++ln) {
                                if (lineAlreadyPresent(ln)) {
                                    overlap = true;
                                    break;
                                }
                            }
                            if (nextStart === prevHunkEndLine + 1 || overlap) {
                                btn.style.display = 'none';
                            }
                        }
                    } else if (expandType === 'below') {
                        // Find last visible line number in this hunk
                        let lastLineNum = null;
                        for (let i = insertIdx - 1; i >= 0; --i) {
                            let row = table.rows[i];
                            if (row.classList.contains('diff-context') || row.classList.contains('diff-added')) {
                                let num = row.querySelectorAll('.diff-line-num')[1];
                                if (num && num.textContent) {
                                    lastLineNum = parseInt(num.textContent);
                                    break;
                                }
                            }
                        }
                        if (lastLineNum === null) return;
                        let start = lastLineNum + 1;
                        let end = Math.min(lines.length + 1, lastLineNum + 1 + contextLines);
                        let inserted = false;
                        for (let ln = start; ln < end; ++ln) {
                            if (lineAlreadyPresent(ln)) continue;
                            let content = lines[ln - 1] || '';
                            let newRow = document.createElement('tr');
                            newRow.className = 'diff-context expanded-context';
                            newRow.innerHTML = `<td class='diff-sign'>&nbsp;</td><td class='diff-line-num'></td><td class='diff-line-num'>${ln}</td><td class='diff-line-content'>${escapeHtml(content)}</td>`;
                            table.tBodies[0].insertBefore(newRow, tr);
                            inserted = true;
                        }
                        // Hide the button if we reached the end or next would overlap
                        if (end > lines.length || !inserted) {
                            btn.style.display = 'none';
                        } else {
                            let nextEnd = Math.min(lines.length + 1, end + contextLines);
                            let overlap = false;
                            for (let ln = end; ln < nextEnd; ++ln) {
                                if (lineAlreadyPresent(ln)) {
                                    overlap = true;
                                    break;
                                }
                            }
                            if (end > lines.length || overlap) {
                                btn.style.display = 'none';
                            }
                        }
                    }
                });
            });
            function escapeHtml(text) {
                var map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
                return text.replace(/[&<>"']/g, function(m) { return map[m]; });
            }
        });
        """
        
        js_path = os.path.join(self.assets_dir, 'script.js')
        with open(js_path, 'w', encoding='utf-8') as f:
            f.write(js_content)
            
        return js_path
    
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
        self.generate_css()
        self.generate_js()
        
        # Build file tree
        file_tree = self._build_file_tree(commit_info['files_changed'])
        # Preload new file contents for dynamic context
        new_file_contents = {}
        for file_info in commit_info['files_changed']:
            filename = file_info['filename']
            try:
                with open(os.path.join(self.repo_path, filename), 'r', encoding='utf-8', errors='replace') as f:
                    new_file_contents[filename] = f.read().splitlines()
            except Exception:
                new_file_contents[filename] = []
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
                {self._render_file_tree(file_tree)}
            </div>
        </div>
        <div class="diff-panel">
'''
        # Add all diffs (all visible, each with anchor)
        for i, file_info in enumerate(commit_info['files_changed']):
            filename = file_info['filename']
            diff_text = self.get_file_diff(commit_hash, filename)
            diff_html, hunk_meta = self.parse_diff_to_html_with_expand(diff_text, filename, i)
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
    
    def parse_diff_to_html_with_expand(self, diff_text, filename, file_idx):
        """
        Like parse_diff_to_html, but adds expandable context controls and returns hunk metadata for JS.
        """
        if not diff_text:
            return "<div class='diff-empty'>No changes</div>", []
        html_lines = []
        lines = diff_text.split('\n')
        in_header = True
        header_lines = []
        old_line_num = 0
        new_line_num = 0
        hunk_meta = []
        for i, line in enumerate(lines):
            if in_header and line.startswith('@@'):
                in_header = False
                match = re.match(r'^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@', line)
                if match:
                    old_line_num = int(match.group('old_start'))
                    new_line_num = int(match.group('new_start'))
                    hunk_start = new_line_num
                # Add header
                if header_lines:
                    html_lines.append("<div class='diff-header'>")
                    for header_line in header_lines:
                        html_lines.append(f"<div>{html.escape(header_line)}</div>")
                    html_lines.append("</div>")
                # Start diff content
                html_lines.append("<div class='diff-content'>")
                html_lines.append(f"<table class='diff-table' data-filename='{html.escape(filename)}' data-file-idx='{file_idx}'>")
            if in_header:
                header_lines.append(line)
                continue
            if line.startswith('@@'):
                # End previous hunk, start new hunk
                html_lines.append(f"<tr class='expand-row'><td colspan='4'><button class='expand-btn' data-expand='above'>Show more above</button></td></tr>")
                html_lines.append(f"<tr class='diff-hunk-header'><td colspan='4'>{html.escape(line)}</td></tr>")
                hunk_start = new_line_num
                hunk_meta.append({'start': new_line_num, 'file': filename})
            elif line.startswith('+'):
                html_lines.append("<tr class='diff-added'>")
                html_lines.append("<td class='diff-sign'>+</td>")
                html_lines.append("<td class='diff-line-num'></td>")
                html_lines.append(f"<td class='diff-line-num'>{new_line_num}</td>")
                html_lines.append(f"<td class='diff-line-content'>{html.escape(line[1:])}</td>")
                html_lines.append("</tr>")
                new_line_num += 1
            elif line.startswith('-'):
                html_lines.append("<tr class='diff-removed'>")
                html_lines.append("<td class='diff-sign'>-</td>")
                html_lines.append(f"<td class='diff-line-num'>{old_line_num}</td>")
                html_lines.append("<td class='diff-line-num'></td>")
                html_lines.append(f"<td class='diff-line-content'>{html.escape(line[1:])}</td>")
                html_lines.append("</tr>")
                old_line_num += 1
            elif line.startswith(' '):
                html_lines.append("<tr class='diff-context'>")
                html_lines.append("<td class='diff-sign'>&nbsp;</td>")
                html_lines.append(f"<td class='diff-line-num'>{old_line_num}</td>")
                html_lines.append(f"<td class='diff-line-num'>{new_line_num}</td>")
                html_lines.append(f"<td class='diff-line-content'>{html.escape(line[1:])}</td>")
                html_lines.append("</tr>")
                old_line_num += 1
                new_line_num += 1
            else:
                html_lines.append("<tr>")
                html_lines.append("<td class='diff-sign'>&nbsp;</td>")
                html_lines.append("<td class='diff-line-num'></td>")
                html_lines.append("<td class='diff-line-num'></td>")
                html_lines.append(f"<td class='diff-line-content'>{html.escape(line)}</td>")
                html_lines.append("</tr>")
        # Add expand below at end of table
        html_lines.append(f"<tr class='expand-row'><td colspan='4'><button class='expand-btn' data-expand='below'>Show more below</button></td></tr>")
        if not in_header:
            html_lines.append("</table>")
            html_lines.append("</div>")
        return "\n".join(html_lines), hunk_meta
    
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
    parser = argparse.ArgumentParser(description='Generate static HTML pages for Git commit reviews')
    parser.add_argument('repo_path', help='Path to the Git repository')
    parser.add_argument('--output-dir', '-o', default='./git-reviews', help='Output directory for generated HTML files')
    parser.add_argument('--commit', '-c', help='Specific commit hash to generate review for')
    parser.add_argument('--num-commits', '-n', type=int, default=1, help='Number of recent commits to generate reviews for')
    parser.add_argument('--template-dir', '-t', help='Directory containing custom templates')
    
    args = parser.parse_args()
    
    try:
        generator = GitCommitReviewGenerator(
            args.repo_path,
            args.output_dir,
            args.commit,
            args.template_dir
        )
        
        generator.generate(args.num_commits)
        
        print(f"\nReview pages generated successfully in {args.output_dir}")
        print(f"Open {os.path.join(args.output_dir, 'index.html')} in your browser to view the reviews")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()