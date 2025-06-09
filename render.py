#!/usr/bin/env python3
"""
Common Render class for generating HTML review pages.

This module contains the shared rendering functionality used by both
Git and SVN review page generators.
"""

import os
import html
import json
import re


class Render:
    """
    A class to handle common rendering functionality for review pages.
    """
    
    def __init__(self, output_dir, assets_dir):
        """
        Initialize the renderer with output directories.
        
        Args:
            output_dir (str): Directory to output the generated HTML files
            assets_dir (str): Directory for CSS/JS assets
        """
        self.output_dir = output_dir
        self.assets_dir = assets_dir
    
    def _normalize_path_for_matching(self, file_path):
        """
        Normalize file paths for matching between scan results and SVN paths.
        
        Args:
            file_path (str): The file path to normalize
            
        Returns:
            str: Normalized path for matching
        """
        # Convert to forward slashes
        normalized = file_path.replace('\\', '/')
        
        # Remove drive letters and common prefixes
        prefixes_to_remove = [
            r'^[A-Za-z]:/[^/]+/',  # Remove drive + first directory (e.g., "D:/serverdev/")
            r'^[A-Za-z]:\\[^\\]+\\',  # Remove drive + first directory (Windows style)
            r'^src/',  # Remove src/ prefix
            r'^trunk/',  # Remove trunk/ prefix
        ]
        
        for prefix_pattern in prefixes_to_remove:
            normalized = re.sub(prefix_pattern, '', normalized, flags=re.IGNORECASE)
        
        return normalized.lower()
    
    def _find_matching_scan_result(self, scan_results, filename, line_num):
        """
        Find scan result that matches the given filename and line number.
        Uses both exact matching and normalized path matching.
        
        Args:
            scan_results (list): List of scan results
            filename (str): The filename to match
            line_num (int): The line number to match
            
        Returns:
            dict or None: Matching scan result or None if not found
        """
        line_str = str(line_num)
        
        # First try exact filename match
        exact_match = next((r for r in scan_results 
                           if str(r['行号']) == line_str and r['文件名'] == filename), None)
        if exact_match:
            return exact_match
        
        # Try normalized path matching
        normalized_target = self._normalize_path_for_matching(filename)
        
        for result in scan_results:
            if str(result['行号']) == line_str:
                normalized_scan_path = self._normalize_path_for_matching(result['文件名'])
                if normalized_scan_path == normalized_target:
                    return result
                
                # Also try basename matching as fallback
                if os.path.basename(result['文件名']) == os.path.basename(filename):
                    return result
        
        # Try custom path mappings (add your specific mappings here)
        custom_mappings = {
            # Example: Map scan result path to SVN path
            # 'D:\\serverdev\\Server\\MatchServer\\MatchManager.cpp': 'src/Server/AllPlayerTeamMatchServer/AllPlayerTeamMatchCourse.cpp',
        }
        
        # Check if SVN filename has a mapping to a scan result path
        for scan_path, svn_path in custom_mappings.items():
            if svn_path == filename:
                for result in scan_results:
                    if str(result['行号']) == line_str and result['文件名'] == scan_path:
                        return result
        
        return None
    
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
        .commit-info, .revision-info {
            display: flex;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }
        .commit-info-item, .revision-info-item {
            margin-right: 24px;
            margin-bottom: 8px;
        }
        .commit-info-label, .revision-info-label {
            font-weight: 600;
            color: #586069;
        }
        .commit-message, .revision-message {
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
            display: none;
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
            max-height: 1000px;
            overflow-y: auto;
        }
        .scan-result-item {
            padding: 8px;
            border-bottom: 1px solid #e1e4e8;
            font-size: 12px;
            cursor: pointer;
            transition: background-color 0.2s ease;
        }
        .scan-result-item:last-child {
            border-bottom: none;
        }
        .scan-result-item:hover {
            background-color: #f6f8fa;
        }
        .scan-result-item.severe:hover {
            background-color: #b5b9f1;
        }
        .scan-result-item.active {
            background-color: #b5b9f1;
            border-left: 3px solid #1976d2;
        }
        .scan-result-item.severe.active {
            background-color: #b5b9f1;
            border-left: 3px solid #d32f2f;
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
        .priority-severe {
            font-weight: bold;
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
            position: relative;
        }
        .diff-line-content {
            padding: 0 8px;
            white-space: pre;
        }
        /* Updated diff colors for better accessibility */
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
        /* Updated scan result styling */
        .scan-result-content {
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-left: 4px solid #f39c12;
            padding: 12px !important;
            margin: 4px 0;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            font-size: 18px;
        }
        .scan-result-content.severe {
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            border-left: 4px solid #dc3545;
        }
        .scan-result-header {
            display: flex;
            align-items: center;
            margin-bottom: 8px;
            font-weight: 600;
        }
        .scan-result-cid {
            background-color: #dc3545;
            color: white;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
            margin-right: 8px;
            font-family: monospace;
        }
        .scan-result-cid.warning {
            background-color: #f39c12;
        }
        .scan-result-count {
            color: #6c757d;
            font-size: 12px;
            margin-left: auto;
        }
        .scan-result-description {
            margin-bottom: 6px;
            font-weight: 500;
            color: #495057;
        }
        .scan-result-suggestion {
            color: #6c757d;
            font-style: italic;
            font-size: 14px;
            line-height: 1.4;
        }
        /* Add severity badge to line number */
        .diff-line-num::after {
            content: '';
            position: absolute;
            right: 4px;
            top: 50%;
            transform: translateY(-50%);
            width: 6px;
            height: 6px;
            border-radius: 50%;
            display: none;
        }
        .scan-result .diff-line-num::after {
            display: block;
            background-color: #ffc107;
        }
        .scan-result.severe .diff-line-num::after {
            background-color: #dc3545;
        }
        .scan-result-highlight {
            animation: scanresultflash 1.2s;
            background: rgba(255, 193, 7, 0.3) !important;
        }
        @keyframes scanresultflash {
            0% { background: rgba(255, 193, 7, 0.3); }
            100% { background: inherit; }
        }
        /* Scan result styles for SVN */
        .has-scan-result {
            position: relative;
        }
        .has-scan-result.scan-result-severe {
            background-color: rgba(220, 53, 69, 0.1) !important;
            border-left: 3px solid #dc3545;
        }
        .has-scan-result.scan-result-general {
            background-color: rgba(255, 193, 7, 0.1) !important;
            border-left: 3px solid #ffc107;
        }
        .has-scan-result .diff-line-num {
            position: relative;
        }
        .has-scan-result.scan-result-severe .diff-line-num::after {
            content: "⚠";
            color: #dc3545;
            font-weight: bold;
            position: absolute;
            right: 2px;
            top: 0;
        }
        .has-scan-result.scan-result-general .diff-line-num::after {
            content: "⚠";
            color: #ffc107;
            font-weight: bold;
            position: absolute;
            right: 2px;
            top: 0;
        }
        .scan-result-detail {
            border-left: 3px solid #6c757d;
        }
        .scan-result-detail.severe {
            border-left-color: #dc3545;
        }
        .scan-result-detail.general {
            border-left-color: #ffc107;
        }
        /* Apply background color only to the content cell */
        .scan-result-detail .diff-line-content {
            background-color: #f8f9fa;
        }
        .scan-result-detail.severe .diff-line-content {
            background-color: #f8d7da;
        }
        .scan-result-detail.general .diff-line-content {
            background-color: #fff3cd;
        }
        /* Keep sign and line number cells transparent */
        .scan-result-detail .diff-sign,
        .scan-result-detail .diff-line-num {
            background-color: transparent !important;
        }
        .scan-result-content {
            padding: 8px 12px;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            font-size: 18px;
            line-height: 1.4;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }
        .scan-result-severity {
            font-weight: bold;
            margin-bottom: 4px;
            color: #495057;
        }
        .scan-result-detail.severe .scan-result-severity {
            color: #dc3545;
        }
        .scan-result-detail.general .scan-result-severity {
            color: #856404;
        }
        .scan-result-description {
            margin-bottom: 4px;
            color: #495057;
            white-space: pre-wrap;
            max-width: 70%;
        }
        .scan-result-suggestion {
            color: #6c757d;
            font-style: italic;
            white-space: pre-wrap;
        }
        .scan-result-highlight {
            animation: highlight-flash 1.6s ease-out;
        }
        @keyframes highlight-flash {
            0% { background-color: #007bff; }
            50% { background-color: rgba(0, 123, 255, 0.3); }
            100% { background-color: transparent; }
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
        .expand-btn {
            background-color: #f6f8fa;
            border: 1px solid #d1d5da;
            border-radius: 3px;
            padding: 4px 8px;
            font-size: 12px;
            cursor: pointer;
            margin-right: 8px;
            color: #586069;
        }
        .expand-btn:hover {
            background-color: #e1e4e8;
        }
        .expand-icon {
            background: none;
            border: none;
            color: #586069;
            cursor: pointer;
            font-size: 12px;
            padding: 0 2px;
        }
        .expand-icon:hover {
            color: #0366d6;
        }
        .expand-row td {
            padding: 2px 4px;
            background-color: #f6f8fa;
            border-bottom: 1px solid #e1e4e8;
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
            // Debug logging function
            function gitDiffLog(...args) {
                const debugLog = false; // Set to true for debugging
                if (debugLog) {
                    console.log('[GitDiff Debug]', ...args);
                }
            }
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
                    // Remove active class from all scan result items
                    document.querySelectorAll('.scan-result-item').forEach(function(scanItem) {
                        scanItem.classList.remove('active');
                    });
                    
                    // Add active class to clicked item
                    item.classList.add('active');
                    
                    const jumpId = item.getAttribute('data-jump');
                    gitDiffLog('Scan result clicked, jumpId:', jumpId);
                    const codeElem = document.getElementById(jumpId);
                    gitDiffLog('Found code element:', codeElem);
                    if (codeElem) {
                        codeElem.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        codeElem.classList.add('scan-result-highlight');
                        setTimeout(() => codeElem.classList.remove('scan-result-highlight'), 1600);
                        gitDiffLog('Scrolled to element successfully');
                    } else {
                        gitDiffLog('ERROR: Could not find element with ID:', jumpId);
                        // Debug: list all scan-result elements
                        const allScanResults = document.querySelectorAll('[id^="scanresult-"]');
                        gitDiffLog('Available scan result IDs:', Array.from(allScanResults).map(el => el.id));
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
            const fileContents = document.getElementById('new-file-contents');
            if (fileContents) {
                const fileContentData = JSON.parse(fileContents.textContent);
                gitDiffLog('File content data loaded:', Object.keys(fileContentData));
                document.querySelectorAll('.expand-icon').forEach(function(btn) {
                    btn.addEventListener('click', function() {
                        const tr = btn.closest('tr');
                        const table = btn.closest('table');
                        const filename = table.getAttribute('data-filename');
                        const lines = fileContentData[filename] || [];
                        let expandType = btn.getAttribute('data-expand');
                        let contextStart = parseInt(btn.getAttribute('data-context-start'));
                        let contextEnd = parseInt(btn.getAttribute('data-context-end'));
                        
                        gitDiffLog(`File data for "${filename}": ${lines ? lines.length : 'NOT FOUND'} lines`);
                        
                        // Handle 10-line expansion
                        if (expandType === 'above-10') {
                            contextStart = Math.max(contextStart, contextEnd - 9);
                        } else if (expandType === 'below-10') {
                            contextEnd = Math.min(contextEnd, contextStart + 9);
                        }
                        
                        // Insert the context lines, but only if not already present
                        gitDiffLog(`===== EXPAND BUTTON CLICKED =====`);
                        gitDiffLog(`Expand type: ${expandType}`);
                        gitDiffLog(`Original context range: ${btn.getAttribute('data-context-start')} to ${btn.getAttribute('data-context-end')}`);
                        gitDiffLog(`Adjusted context range: ${contextStart} to ${contextEnd}`);
                        gitDiffLog(`File: ${filename}`);
                        gitDiffLog(`Total lines in file: ${lines.length}`);
                        
                        let insertedRows = [];
                        let visibleLines = new Set();
                        let allRows = Array.from(table.querySelectorAll('tr'));
                        allRows.forEach((row, i) => {
                            let lineNumCells = row.querySelectorAll('.diff-line-num');
                            if (lineNumCells.length >= 2) {
                                for (let j = 0; j < lineNumCells.length; j++) {
                                    let lineText = lineNumCells[j].textContent.trim();
                                    let lineNum = parseInt(lineText);
                                    if (!isNaN(lineNum) && lineNum > 0) {
                                        visibleLines.add(lineNum);
                                    }
                                }
                            }
                        });
                        
                        // Collect all lines to insert first (skip already visible lines)
                        let linesToInsert = [];
                        gitDiffLog(`Collecting lines to insert from ${contextStart} to ${contextEnd}`);
                        for (let ln = contextStart; ln <= contextEnd; ++ln) {
                            if (!visibleLines.has(ln)) {
                                let content = lines[ln - 1] || '';
                                gitDiffLog(`Line ${ln}: "${content}" (array index: ${ln - 1})`);
                                linesToInsert.push({lineNum: ln, content: content});
                            } else {
                                gitDiffLog(`Line ${ln}: SKIPPED (already visible)`);
                            }
                        }
                        gitDiffLog(`Total lines to insert: ${linesToInsert.length}`);
                        
                        // Find the insertion point for the entire block
                        let insertionPoint = null;
                        let rows = Array.from(table.tBodies[0].rows);
                        
                        for (let i = 0; i < rows.length; i++) {
                            let row = rows[i];
                            let lineNumCells = row.querySelectorAll('.diff-line-num');
                            if (lineNumCells.length >= 2) {
                                let maxLineNum = 0;
                                for (let j = 0; j < lineNumCells.length; j++) {
                                    let lineText = lineNumCells[j].textContent.trim();
                                    let lineNum = parseInt(lineText);
                                    if (!isNaN(lineNum) && lineNum > 0) {
                                        maxLineNum = Math.max(maxLineNum, lineNum);
                                    }
                                }
                                if (maxLineNum > 0 && maxLineNum > contextStart) {
                                    insertionPoint = row;
                                    break;
                                }
                            }
                        }
                        
                        if (!insertionPoint) {
                            insertionPoint = tr;
                        }
                        
                        // Insert all lines as a block in the correct order
                        gitDiffLog(`Inserting ${linesToInsert.length} lines before insertion point`);
                        linesToInsert.forEach(function(lineInfo, index) {
                            let newRow = document.createElement('tr');
                            newRow.className = 'diff-context expanded-context';
                            newRow.innerHTML = `<td class='diff-sign'>&nbsp;</td><td class='diff-line-num'></td><td class='diff-line-num'>${lineInfo.lineNum}</td><td class='diff-line-content'>${escapeHtml(lineInfo.content)}</td>`;
                            gitDiffLog(`Inserting line ${lineInfo.lineNum}: "${lineInfo.content}"`);
                            table.tBodies[0].insertBefore(newRow, insertionPoint);
                            insertedRows.push(newRow);
                        });
                        
                        // For 10-line expansions, update the button range and keep it
                        if (expandType.endsWith('-10')) {
                            let originalStart = parseInt(btn.getAttribute('data-context-start'));
                            let originalEnd = parseInt(btn.getAttribute('data-context-end'));
                            
                            if (expandType === 'above-10') {
                                let newEnd = contextStart - 1;
                                if (newEnd >= originalStart) {
                                    btn.setAttribute('data-context-end', newEnd);
                                } else {
                                    tr.remove();
                                }
                            } else if (expandType === 'below-10') {
                                let newStart = contextEnd + 1;
                                if (newStart <= originalEnd) {
                                    btn.setAttribute('data-context-start', newStart);
                                } else {
                                    tr.remove();
                                }
                            }
                        } else {
                            tr.remove();
                        }
                    });
                });
            }
            
            function escapeHtml(text) {
                var map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
                return text.replace(/[&<>"']/g, function(m) { return map[m]; });
            }
            
            // Auto-scroll scan results panel to keep highlighted item visible
            function scrollScanResultItemIntoView(scanResultItem) {
                if (!scanResultItem) return;
                
                gitDiffLog('Auto-scrolling scan result item into view:', scanResultItem);
                
                // Find the scan results panel container
                const scanResultsList = document.querySelector('.scan-results-list');
                if (!scanResultsList) {
                    gitDiffLog('ERROR: .scan-results-list not found for auto-scroll');
                    return;
                }
                
                // Get positions
                const itemRect = scanResultItem.getBoundingClientRect();
                const containerRect = scanResultsList.getBoundingClientRect();
                
                gitDiffLog('Scroll container info:', {
                    containerTop: containerRect.top,
                    containerBottom: containerRect.bottom,
                    containerHeight: containerRect.height,
                    containerScrollTop: scanResultsList.scrollTop,
                    containerScrollHeight: scanResultsList.scrollHeight
                });
                
                gitDiffLog('Item info:', {
                    itemTop: itemRect.top,
                    itemBottom: itemRect.bottom,
                    itemHeight: itemRect.height
                });
                
                // Check if item is visible within container
                const itemTopRelativeToContainer = itemRect.top - containerRect.top;
                const itemBottomRelativeToContainer = itemRect.bottom - containerRect.top;
                
                gitDiffLog('Item relative position:', {
                    itemTopRelative: itemTopRelativeToContainer,
                    itemBottomRelative: itemBottomRelativeToContainer,
                    containerHeight: containerRect.height
                });
                
                const isItemVisible = itemTopRelativeToContainer >= 0 && itemBottomRelativeToContainer <= containerRect.height;
                gitDiffLog('Is item visible:', isItemVisible);
                
                if (!isItemVisible) {
                    // Calculate scroll position to center the item in the container
                    const itemCenterRelativeToDocument = itemRect.top + (itemRect.height / 2);
                    const containerCenterRelativeToDocument = containerRect.top + (containerRect.height / 2);
                    const scrollOffset = itemCenterRelativeToDocument - containerCenterRelativeToDocument;
                    
                    const newScrollTop = scanResultsList.scrollTop + scrollOffset;
                    
                    gitDiffLog('Scrolling scan results panel:', {
                        currentScrollTop: scanResultsList.scrollTop,
                        scrollOffset: scrollOffset,
                        newScrollTop: newScrollTop
                    });
                    
                    // Smooth scroll to the new position
                    scanResultsList.scrollTo({
                        top: Math.max(0, newScrollTop),
                        behavior: 'smooth'
                    });
                } else {
                    gitDiffLog('Item is already visible, no scroll needed');
                }
            }
            
            // Auto-highlight scan results based on scroll position
            function updateScanResultHighlightOnScroll(scrollContainer, containerName) {
                gitDiffLog('=== SCROLL EVENT TRIGGERED (' + (containerName || 'unknown') + ') ===');
                
                // Determine the actual scroll container to use
                let actualContainer = scrollContainer;
                if (!actualContainer) {
                    actualContainer = document.querySelector('.diff-panel') || document.body;
                }
                
                gitDiffLog('Using scroll container:', containerName || 'fallback', actualContainer);
                
                // Calculate viewport based on the container
                let viewportTop, viewportBottom, viewportCenter, clientHeight;
                
                if (actualContainer === window || actualContainer === document.body || actualContainer === document.documentElement) {
                    // For window/body scroll, use window dimensions
                    viewportTop = window.pageYOffset || document.documentElement.scrollTop;
                    clientHeight = window.innerHeight;
                    viewportBottom = viewportTop + clientHeight;
                    viewportCenter = viewportTop + (clientHeight / 2);
                    gitDiffLog('Using window scroll - pageYOffset:', viewportTop, 'innerHeight:', clientHeight);
                } else {
                    // For element scroll, use element dimensions
                    viewportTop = actualContainer.scrollTop;
                    clientHeight = actualContainer.clientHeight;
                    viewportBottom = viewportTop + clientHeight;
                    viewportCenter = viewportTop + (clientHeight / 2);
                    gitDiffLog('Using element scroll - scrollTop:', viewportTop, 'clientHeight:', clientHeight);
                }
                
                gitDiffLog('Viewport - Top:', viewportTop, 'Center:', viewportCenter, 'Bottom:', viewportBottom, 'ClientHeight:', clientHeight);
                
                // Find all scan result elements in the code
                const scanResultElements = document.querySelectorAll('[id^="scanresult-"]');
                gitDiffLog('Total scan result elements found:', scanResultElements.length);
                
                if (scanResultElements.length === 0) {
                    gitDiffLog('WARNING: No scan result elements found with id starting with "scanresult-"');
                    // Let's check what IDs are actually available
                    const allElementsWithId = document.querySelectorAll('[id]');
                    gitDiffLog('All elements with IDs:', Array.from(allElementsWithId).map(el => el.id));
                    return;
                }
                
                let closestScanResult = null;
                let closestDistance = Infinity;
                let visibleCount = 0;
                
                scanResultElements.forEach(function(element, index) {
                    try {
                        const rect = element.getBoundingClientRect();
                        
                        // Calculate element position relative to the scroll container
                        let elementTop, elementBottom, elementCenter;
                        
                        if (actualContainer === window || actualContainer === document.body || actualContainer === document.documentElement) {
                            // For window/body scroll, use absolute position
                            elementTop = rect.top + viewportTop;
                            elementBottom = elementTop + rect.height;
                            elementCenter = elementTop + (rect.height / 2);
                        } else {
                            // For element scroll, calculate relative to container
                            const containerRect = actualContainer.getBoundingClientRect();
                            elementTop = rect.top - containerRect.top + actualContainer.scrollTop;
                            elementBottom = elementTop + rect.height;
                            elementCenter = elementTop + (rect.height / 2);
                        }
                        
                        // Calculate distance from viewport center
                        const distance = Math.abs(elementCenter - viewportCenter);
                        
                        // Check if element is visible in viewport
                        const isVisible = elementTop < viewportBottom && elementBottom > viewportTop;
                        
                        gitDiffLog('Element ' + (index + 1) + '/' + scanResultElements.length + ':', {
                            id: element.id,
                            elementTop: elementTop,
                            elementBottom: elementBottom,
                            elementCenter: elementCenter,
                            distance: distance,
                            isVisible: isVisible,
                            rectHeight: rect.height
                        });
                        
                        if (isVisible) {
                            visibleCount++;
                            if (distance < closestDistance) {
                                closestDistance = distance;
                                closestScanResult = element;
                                gitDiffLog('New closest scan result:', element.id, 'Distance:', distance);
                            }
                        }
                    } catch (error) {
                        gitDiffLog('Error processing element:', element.id, error);
                    }
                });
                
                gitDiffLog('Summary - Visible elements:', visibleCount, 'Closest:', closestScanResult ? closestScanResult.id : 'none');
                
                if (closestScanResult) {
                    const scanResultId = closestScanResult.id;
                    gitDiffLog('Processing closest scan result:', scanResultId);
                    
                    // Find corresponding scan result item in the panel
                    const scanResultItem = document.querySelector(`.scan-result-item[data-jump="${scanResultId}"]`);
                    gitDiffLog('Found scan result item in panel:', !!scanResultItem);
                    
                    if (scanResultItem) {
                        // Remove active class from all scan result items
                        const allScanItems = document.querySelectorAll('.scan-result-item');
                        gitDiffLog('Total scan result items in panel:', allScanItems.length);
                        
                        allScanItems.forEach(function(item) {
                            item.classList.remove('active');
                        });
                        
                        // Add active class to the corresponding item
                        scanResultItem.classList.add('active');
                        gitDiffLog('Successfully highlighted scan result item:', scanResultId);
                        
                        // Auto-scroll the scan results panel to keep the highlighted item visible
                        scrollScanResultItemIntoView(scanResultItem);
                    } else {
                        gitDiffLog('ERROR: Could not find scan result item with data-jump="' + scanResultId + '"');
                        // Debug: show all available data-jump values
                        const allScanItems = document.querySelectorAll('.scan-result-item[data-jump]');
                        gitDiffLog('Available data-jump values:', Array.from(allScanItems).map(item => item.getAttribute('data-jump')));
                    }
                } else {
                    gitDiffLog('No closest scan result found - no elements visible or no elements exist');
                }
                
                gitDiffLog('=== SCROLL EVENT COMPLETED ===');
            }
            
            // Add scroll event listener with throttling
            let scrollTimeout;
            
            // Try to find the actual scrollable container
            const diffPanel = document.querySelector('.diff-panel');
            const reviewMain = document.querySelector('.review-main');
            const body = document.body;
            const htmlElement = document.documentElement;
            
            gitDiffLog('Container elements found:');
            gitDiffLog('- .diff-panel:', !!diffPanel);
            gitDiffLog('- .review-main:', !!reviewMain);
            gitDiffLog('- body:', !!body);
            gitDiffLog('- html:', !!htmlElement);
            
            // Check which elements are actually scrollable
            function checkScrollable(element, name) {
                if (!element) return false;
                const hasVerticalScroll = element.scrollHeight > element.clientHeight;
                const overflowY = window.getComputedStyle(element).overflowY;
                gitDiffLog(name + ' scroll info:', {
                    scrollHeight: element.scrollHeight,
                    clientHeight: element.clientHeight,
                    hasVerticalScroll: hasVerticalScroll,
                    overflowY: overflowY,
                    scrollTop: element.scrollTop
                });
                return hasVerticalScroll;
            }
            
            checkScrollable(diffPanel, '.diff-panel');
            checkScrollable(reviewMain, '.review-main');
            checkScrollable(body, 'body');
            checkScrollable(htmlElement, 'html');
            
            function setupScrollListener(element, name) {
                if (!element) return false;
                
                gitDiffLog('Setting up scroll listener on:', name);
                element.addEventListener('scroll', function() {
                    gitDiffLog('SCROLL EVENT FIRED on ' + name + ' - scrollTop:', element.scrollTop);
                    clearTimeout(scrollTimeout);
                    scrollTimeout = setTimeout(function() {
                        updateScanResultHighlightOnScroll(element, name);
                    }, 100);
                });
                return true;
            }
            
            // Try to set up scroll listeners on multiple potential containers
            let listenersAdded = 0;
            if (setupScrollListener(diffPanel, '.diff-panel')) listenersAdded++;
            if (setupScrollListener(reviewMain, '.review-main')) listenersAdded++;
            if (setupScrollListener(body, 'body')) listenersAdded++;
            if (setupScrollListener(window, 'window')) listenersAdded++;
            
            gitDiffLog('Total scroll listeners added:', listenersAdded);
            
            // Also run once on page load to set initial state
            gitDiffLog('Running initial scan result highlight check');
            setTimeout(function() {
                updateScanResultHighlightOnScroll(diffPanel || body, 'initial');
            }, 500);
        });
        """
        
        js_path = os.path.join(self.assets_dir, 'script.js')
        with open(js_path, 'w', encoding='utf-8') as f:
            f.write(js_content)
            
        return js_path
    
    def render_scan_results_panel(self, scan_results):
        """
        Render the scan results panel HTML.
        
        Args:
            scan_results (list): List of scan results
            
        Returns:
            str: HTML for scan results panel
        """
        # Sort scan results by filename and then by line number
        sorted_scan_results = sorted(scan_results, key=lambda r: (r['文件名'], int(r['行号'])))
        
        html_parts = ['<div class="scan-results-list">']
        
        for result in sorted_scan_results:
            severity_class = 'severe' if result['严重程度'] == '严重' else ''
            show_text = '特别注意' if result['严重程度'] == '严重' else '需关注'
            priority_class = 'priority-severe' if result['严重程度'] == '严重' else 'priority-normal'
            safe_filename = result['文件名'].replace('/', '-').replace('\\', '-').replace('.', '-')
            jump_id = f"scanresult-{safe_filename}-{result['行号']}"
            issue_count = result.get('问题数量', 1)
            count_text = f" ({issue_count} issues)" if issue_count > 1 else ""
            html_parts.append(f'''
                <div class="scan-result-item {severity_class}" data-line="{result['行号']}" data-jump="{jump_id}">
                    <div class="{priority_class}">[{show_text}]</div>
                    <div class="file-name">文件名：{html.escape(result['文件名'])}</div>
                    <div class="line-number">行号： {result['行号']}{count_text}</div>
                </div>
''')
        
        html_parts.append('</div>')
        return '\n'.join(html_parts)
    
    def parse_diff_to_html_with_expand(self, diff_text, filename, file_idx, scan_results, repo_path):
        """
        Parse diff to HTML with expandable context and scan results.
        Treats scan results as fake diff hunks with [-10, +10] context to unify the rendering logic.
        
        Args:
            diff_text (str): The diff text to parse
            filename (str): The filename being diffed
            file_idx (int): Index of the file in the file list
            scan_results (list): List of scan results
            repo_path (str): Path to the repository for reading file contents
            
        Returns:
            tuple: (HTML string, hunk metadata)
        """
        # Get the full new file content for context
        try:
            # Try multiple possible locations for the file with proper Windows path handling
            file_paths = []
            
            # Normalize paths for Windows
            repo_path_normalized = repo_path.replace('\\', '/')
            repo_parent = os.path.dirname(repo_path)
            repo_parent_normalized = repo_parent.replace('\\', '/')
            
            # Try exact path
            file_paths.append(os.path.join(repo_path, filename))
            
            # Try with normalized repo path (this pattern worked in scan results loading)
            file_paths.append(repo_path_normalized + '/' + filename.replace('\\', '/'))
            
            # Try trunk path 
            file_paths.append(os.path.join(repo_path, 'trunk', filename))
            
            # Try parent directory
            file_paths.append(os.path.join(repo_parent, filename))
            
            # Try parent/trunk
            file_paths.append(os.path.join(repo_parent, 'trunk', filename))
            
            # Try with parent normalized (another pattern that might work)
            file_paths.append(repo_parent_normalized + '/' + filename.replace('\\', '/'))
            
            # Try without src/ prefix if present
            if filename.startswith('src/'):
                filename_without_src = filename[4:]  # Remove 'src/' prefix
                file_paths.append(os.path.join(repo_path, filename_without_src))
                file_paths.append(repo_path_normalized + '/' + filename_without_src.replace('\\', '/'))
                file_paths.append(os.path.join(repo_parent, filename_without_src))
                file_paths.append(repo_parent_normalized + '/' + filename_without_src.replace('\\', '/'))
            
            full_lines = []
            print(f"DEBUG: Looking for file {filename}")
            print(f"DEBUG: repo_path = {repo_path}")
            print(f"DEBUG: repo_path_normalized = {repo_path_normalized}")
            print(f"DEBUG: repo_parent = {repo_parent}")
            print(f"DEBUG: Trying these paths:")
            for file_path in file_paths:
                print(f"  - {file_path} ({'EXISTS' if os.path.exists(file_path) else 'NOT FOUND'})")
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        full_lines = f.read().splitlines()
                        print(f"DEBUG: Successfully loaded {len(full_lines)} lines from {file_path}")
                        break
            
            if not full_lines:
                error_msg = f"CRITICAL ERROR: Could not find file {filename} in any of these locations: {file_paths}"
                print(error_msg)
                raise FileNotFoundError(error_msg)
                
        except Exception as e:
            print(f"Error reading file {filename} from {file_paths}: {str(e)}")
            raise
        
        # Parse original diff hunks
        all_hunks = []
        if diff_text:
            lines = diff_text.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i]
                if line.startswith('@@'):
                    match = re.match(r'^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@', line)
                    if match:
                        new_start = int(match.group('new_start'))
                        new_count = int(match.group('new_count') or '1')
                        all_hunks.append({
                            'type': 'real_diff',
                            'diff_idx': i,
                            'new_start': new_start,
                            'new_count': new_count,
                            'original_lines': lines
                        })
                i += 1
        
        # Calculate actual line coverage for real diff hunks by parsing the diff content
        covered_lines = set()
        print(f"\n===== DEBUG: Processing file {filename} =====")
        print(f"Total real diff hunks: {len([h for h in all_hunks if h['type'] == 'real_diff'])}")
        
        for hunk in all_hunks:
            if hunk['type'] == 'real_diff':
                print(f"\nProcessing real diff hunk starting at line {hunk['new_start']}")
                # Parse the actual diff lines to see which new file lines are covered
                lines = hunk['original_lines']
                hunk_header = lines[hunk['diff_idx']]
                print(f"Hunk header: {hunk_header}")
                match = re.match(r'^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@', hunk_header)
                if match:
                    cur_new = int(match.group('new_start'))
                    original_cur_new = cur_new
                    j = hunk['diff_idx'] + 1
                    covered_lines_in_hunk = []
                    while j < len(lines) and not lines[j].startswith('@@'):
                        l = lines[j]
                        if l.startswith('+') or l.startswith(' '):
                            covered_lines.add(cur_new)
                            covered_lines_in_hunk.append(cur_new)
                            cur_new += 1
                        # Deleted lines (starting with '-') don't increment new line number
                        j += 1
                    print(f"  Real diff covers lines: {sorted(covered_lines_in_hunk)} (range: {original_cur_new}-{cur_new-1})")
        
        print(f"\nTotal covered lines by real diffs: {sorted(covered_lines)}")
        
        # Filter scan results for this file using proper path matching
        file_scan_results = []
        for r in scan_results:
            if self._find_matching_scan_result([r], filename, r['行号']):
                file_scan_results.append(r)
        
        print(f"before sort, File scan results: {file_scan_results}")
        # Sort scan results by line number to ensure smaller line numbers come first
        file_scan_results.sort(key=lambda r: int(r['行号']))
        print(f"after sort, File scan results: {file_scan_results}")
        
        scan_lines = [int(r['行号']) for r in file_scan_results]
        print(f"\nScan lines to process: {scan_lines}")
        
        for scan_line in scan_lines:
            context_start = max(1, scan_line - 10)
            context_end = min(len(full_lines), scan_line + 10)
            print(f"\nProcessing scan line {scan_line}, context range [{context_start}-{context_end}]")
            
            # Check if the scan line itself is covered by a real diff
            scan_line_covered = scan_line in covered_lines
            
            if scan_line_covered:
                print(f"  Scan line {scan_line} is covered by real diff. SKIPPING scan context hunk.")
            else:
                # Check for overlaps with real diffs and adjust context range
                # Find non-overlapping segments of the context range
                segments = []
                current_start = context_start
                
                # Sort covered lines to find gaps
                overlapping_covered = sorted([ln for ln in covered_lines if context_start <= ln <= context_end])
                print(f"  Lines in context range already covered by real diffs: {overlapping_covered}")
                
                if not overlapping_covered:
                    # No overlap, use full context
                    segments = [(context_start, context_end)]
                else:
                    # Find non-overlapping segments
                    segments = []
                    last_covered = context_start - 1
                    for covered_line in overlapping_covered + [context_end + 1]:  # Add sentinel
                        if covered_line > last_covered + 1:
                            # There's a gap - add segment
                            seg_start = last_covered + 1
                            seg_end = covered_line - 1
                            if seg_start <= context_end and seg_start <= seg_end:
                                final_seg = (seg_start, min(seg_end, context_end))
                                segments.append(final_seg)
                        last_covered = covered_line
                
                print(f"  Non-overlapping segments: {segments}")
                
                # Create scan context hunks for each non-overlapping segment
                for seg_start, seg_end in segments:
                    if seg_start <= seg_end:
                        context_count = seg_end - seg_start + 1
                        print(f"  Creating scan context hunk for [{seg_start}-{seg_end}] (scan line: {scan_line})")
                        all_hunks.append({
                            'type': 'scan_context',
                            'new_start': seg_start,
                            'new_count': context_count,
                            'scan_line': scan_line
                        })
        
        # Sort all hunks by start line without merging
        all_hunks.sort(key=lambda h: h['new_start'])
        
        print(f"\n===== FINAL HUNK LIST =====")
        for i, hunk in enumerate(all_hunks):
            hunk_end = hunk['new_start'] + hunk['new_count'] - 1
            if hunk['type'] == 'real_diff':
                print(f"  {i}: Real diff hunk [{hunk['new_start']}-{hunk_end}]")
            else:
                print(f"  {i}: Scan context hunk [{hunk['new_start']}-{hunk_end}] (scan line: {hunk['scan_line']})")
        print(f"===========================\n")
        
        # Now render all hunks using unified logic
        html_lines = []
        html_lines.append("<div class='diff-content'>")
        html_lines.append(f"<table class='diff-table' data-filename='{html.escape(filename)}' data-file-idx='{file_idx}'>")
        
        prev_hunk_end = 0
        hunk_meta = []
        
        for hunk in all_hunks:
            hunk_start = hunk['new_start']
            hunk_count = hunk['new_count']
            hunk_end = hunk_start + hunk_count - 1
            
            # Add expansion button for gap before this hunk
            if hunk_start > prev_hunk_end + 1:
                context_start = prev_hunk_end + 1
                context_end = hunk_start - 1
                html_lines.append(
                    f"<tr class='expand-row'><td class='diff-line-num'></td><td class='diff-line-num'></td><td class='diff-line-content'><button class='expand-icon' data-expand='above-10' data-context-start='{context_start}' data-context-end='{context_end}' title='向上10行'>▲10</button> <button class='expand-icon' data-expand='above' data-context-start='{context_start}' data-context-end='{context_end}' title='向上到上一个diff块'>▲</button></td></tr>"
                )
            
            # Render hunk content
            if hunk['type'] == 'real_diff':
                # Render real diff hunk
                self._render_real_diff_hunk(html_lines, hunk, scan_results, filename, full_lines)
            elif hunk['type'] == 'scan_context':
                # Render scan context as fake hunk
                self._render_scan_context_hunk(html_lines, hunk, scan_results, filename, full_lines)
            
            hunk_meta.append({'start': hunk_start, 'file': filename})
            prev_hunk_end = hunk_end
        
        # Add expansion button for remaining lines after last hunk
        if prev_hunk_end < len(full_lines):
            context_start = prev_hunk_end + 1
            context_end = len(full_lines)
            html_lines.append(
                f"<tr class='expand-row'><td class='diff-line-num'></td><td class='diff-line-num'></td><td class='diff-line-content'><button class='expand-icon' data-expand='below-10' data-context-start='{context_start}' data-context-end='{context_end}' title='向下10行'>▼10</button> <button class='expand-icon' data-expand='below' data-context-start='{context_start}' data-context-end='{context_end}' title='向下到下一个diff块'>▼</button></td></tr>"
            )
        
        html_lines.append("</table>")
        html_lines.append("</div>")
        return "\n".join(html_lines), hunk_meta
    
    def _render_real_diff_hunk(self, html_lines, hunk, scan_results, filename, full_lines):
        """Render a real diff hunk."""
        lines = hunk['original_lines']
        hunk_header_line = lines[hunk['diff_idx']]
        html_lines.append(f"<tr class='diff-hunk-header'><td colspan='4'>{html.escape(hunk_header_line)}</td></tr>")
        
        # Parse the hunk to get starting line numbers
        match = re.match(r'^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@', hunk_header_line)
        cur_old = int(match.group('old_start')) if match else None
        cur_new = hunk['new_start']
        
        # Track which scan results have already been rendered in this hunk to avoid duplicates
        rendered_scan_results = set()
        
        # Render hunk lines
        j = hunk['diff_idx'] + 1
        while j < len(lines) and not lines[j].startswith('@@'):
            l = lines[j]
            
            # Check for scan results on this line
            scan_line_num = None
            if l.startswith('+'):
                scan_line_num = cur_new
            elif l.startswith('-'):
                scan_line_num = cur_old  
            elif l.startswith(' '):
                scan_line_num = cur_new
                
            if scan_line_num:
                scan_result = self._find_matching_scan_result(scan_results, filename, scan_line_num)
                print(f"Scan result: {scan_result}, filename: {filename}, scan_line_num: {scan_line_num}")
                if scan_result:
                    # Create a unique key for this scan result
                    scan_result_key = (scan_result['文件名'], scan_result['行号'], scan_result['问题描述'])
                    
                    # Only render if we haven't rendered this scan result in this hunk yet
                    if scan_result_key not in rendered_scan_results:
                        rendered_scan_results.add(scan_result_key)
                        
                        # Use the scan result's filename to ensure jump ID consistency
                        safe_filename = scan_result['文件名'].replace('/', '-').replace('\\', '-').replace('.', '-')
                        jump_id = f"scanresult-{safe_filename}-{scan_line_num}"
                        remind_text = '需特别注意' if scan_result['严重程度'] == '严重' else '需注意'
                        severity_class = 'severe' if scan_result['严重程度'] == '严重' else ''
                        cid_class = '' if scan_result['严重程度'] == '严重' else 'warning'
                        # Generate a fake CID number for display
                        cid_number = f"CID {hash(scan_result['问题描述']) % 1000000:06d}"
                        # Get the count of issues
                        issue_count = scan_result.get('问题数量', 1)
                        count_text = f"({issue_count} issues)" if issue_count > 1 else ""
                        html_lines.append(f"<tr class='scan-result' id='{jump_id}'><td class='diff-sign'></td><td class='diff-line-num'></td><td class='diff-line-num'></td><td class='diff-line-content scan-result-content {severity_class}'><div class='scan-result-header'><span class='scan-result-cid {cid_class}'>{cid_number}</span><span>{remind_text}</span><span class='scan-result-count'>{count_text}</span></div><div class='scan-result-description'>{html.escape(scan_result['问题描述'])}</div><div class='scan-result-suggestion'>{html.escape(scan_result['修改意见'])}</div></td></tr>")
            
            # Render the actual diff line
            if l.startswith('+'):
                html_lines.append(f"<tr class='diff-added'><td class='diff-sign'>+</td><td class='diff-line-num'></td><td class='diff-line-num'>{cur_new}</td><td class='diff-line-content'>{html.escape(l[1:])}</td></tr>")
                cur_new += 1
            elif l.startswith('-'):
                html_lines.append(f"<tr class='diff-removed'><td class='diff-sign'>-</td><td class='diff-line-num'>{cur_old}</td><td class='diff-line-num'></td><td class='diff-line-content'>{html.escape(l[1:])}</td></tr>")
                cur_old += 1
            elif l.startswith(' '):
                html_lines.append(f"<tr class='diff-context'><td class='diff-sign'>&nbsp;</td><td class='diff-line-num'>{cur_old}</td><td class='diff-line-num'>{cur_new}</td><td class='diff-line-content'>{html.escape(l[1:])}</td></tr>")
                cur_old += 1
                cur_new += 1
            j += 1
    
    def _render_scan_context_hunk(self, html_lines, hunk, scan_results, filename, full_lines):
        """Render a scan context as a fake diff hunk."""
        start_line = hunk['new_start']
        end_line = hunk['new_start'] + hunk['new_count'] - 1
        scan_line = hunk['scan_line']
        
        html_lines.append(f"<tr class='diff-hunk-header'><td colspan='4'>@@ Scan Result Context: Lines {start_line}-{end_line} @@</td></tr>")
        
        for ln in range(start_line, end_line + 1):
            content = full_lines[ln-1] if 0 <= ln-1 < len(full_lines) else ''
            
            # Always render the original line content first
            html_lines.append(f"<tr class='diff-context'><td class='diff-sign'>&nbsp;</td><td class='diff-line-num'></td><td class='diff-line-num'>{ln}</td><td class='diff-line-content'>{html.escape(content)}</td></tr>")
            
            # Check if this line has a scan result and add it as an additional row
            scan_result = self._find_matching_scan_result(scan_results, filename, ln)
            if scan_result:
                # Use the scan result's filename to ensure jump ID consistency  
                safe_filename = scan_result['文件名'].replace('/', '-').replace('\\', '-').replace('.', '-')
                jump_id = f"scanresult-{safe_filename}-{ln}"
                severity_class = 'severe' if scan_result['严重程度'] == '严重' else ''
                cid_class = '' if scan_result['严重程度'] == '严重' else 'warning'
                # Generate a fake CID number for display
                cid_number = f"CID {hash(scan_result['问题描述']) % 1000000:06d}"
                # Get the count of issues
                issue_count = scan_result.get('问题数量', 1)
                count_text = f"({issue_count} issues)" if issue_count > 1 else ""
                html_lines.append(f"<tr class='scan-result' id='{jump_id}'><td class='diff-sign'></td><td class='diff-line-num'></td><td class='diff-line-num'></td><td class='diff-line-content scan-result-content {severity_class}'><div class='scan-result-header'><span class='scan-result-cid {cid_class}'>{cid_number}</span><span>警告</span><span class='scan-result-count'>{count_text}</span></div><div class='scan-result-description'>{html.escape(scan_result['问题描述'])}</div><div class='scan-result-suggestion'>{html.escape(scan_result['修改意见'])}</div></td></tr>") 
    
    def generate_review_page(self, commit_info, file_tree, scan_results, new_file_contents, diff_htmls):
        """
        Generate a review page HTML content.
        
        Args:
            commit_info (dict): Commit information including hash/revision, author, date, etc.
            file_tree (dict): File tree structure
            scan_results (list): List of scan results
            new_file_contents (dict): Dictionary of new file contents
            diff_htmls (list): List of diff HTML content for each file
            
        Returns:
            str: Complete HTML content for the review page
        """
        # Generate CSS and JS
        self.generate_css()
        self.generate_js()
        
        # Determine if this is a Git commit or SVN revision
        is_svn = 'revision' in commit_info
        id_field = 'revision' if is_svn else 'hash'
        id_label = 'Revision' if is_svn else 'Commit'
        info_class = 'revision-info' if is_svn else 'commit-info'
        message_class = 'revision-message' if is_svn else 'commit-message'
        
        # Build HTML content
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Review: {html.escape(commit_info['subject'])}</title>
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <div class="header">
        <h1>{html.escape(commit_info['subject'])}</h1>
        <div class="{info_class}">
            <div class="{info_class}-item">
                <div class="{info_class}-label">Author</div>
                <div>{html.escape(commit_info['author_name'])} &lt;{html.escape(commit_info['author_email'])}&gt;</div>
            </div>
            <div class="{info_class}-item">
                <div class="{info_class}-label">{id_label}</div>
                <div>{commit_info[id_field]}</div>
            </div>
            <div class="{info_class}-item">
                <div class="{info_class}-label">Date</div>
                <div>{commit_info['date']}</div>
            </div>
        </div>
        <div class="{message_class}">{html.escape(commit_info['body'])}</div>
    </div>
    <div class="review-main">
        <div class="file-list-panel">
            <input type="text" class="file-search-box" placeholder="Search files..." />
            <div class="file-list file-tree-container">
                {self._render_file_tree(file_tree)}
            </div>
        </div>
        <div class="scan-results-panel">
            {self.render_scan_results_panel(scan_results)}
        </div>
        <div class="diff-panel">
'''
        # Add all diffs
        for i, diff_html in enumerate(diff_htmls):
            html_content += f'''
            <div id="diff-{i}" class="diff-container">
                {diff_html}
            </div>
'''
        # Embed new file contents as JSON for JS
        html_content += f'''<script id="new-file-contents" type="application/json">{json.dumps(new_file_contents)}</script>'''
        html_content += '''
        </div>
    </div>
    <div class="footer">
        Generated by ''' + ('SVN' if is_svn else 'Git') + ''' Review Generator
    </div>
    <script src="assets/script.js"></script>
</body>
</html>
'''
        return html_content
    
    def debug_path_matching(self, scan_results, svn_files):
        """
        Debug function to show how paths are being normalized and matched.
        
        Args:
            scan_results (list): List of scan results
            svn_files (list): List of SVN file paths
        """
        print("\n===== PATH MATCHING DEBUG =====")
        
        print("\nScan Result Paths:")
        for result in scan_results:
            original = result['文件名']
            normalized = self._normalize_path_for_matching(original)
            print(f"  Original: {original}")
            print(f"  Normalized: {normalized}")
            print(f"  Basename: {os.path.basename(original)}")
            print()
        
        print("SVN File Paths:")
        for svn_file in svn_files:
            normalized = self._normalize_path_for_matching(svn_file)
            print(f"  Original: {svn_file}")
            print(f"  Normalized: {normalized}")
            print(f"  Basename: {os.path.basename(svn_file)}")
            print()
        
        print("================================\n") 