#!/usr/bin/env python3
"""
Common Render class for generating HTML review pages.

This module contains the shared rendering functionality used by both
Git and SVN review page generators.
"""

import os
import html
import json


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
            font-size: 12px;
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
            background-color: #f8f9fa;
            border-left: 3px solid #6c757d;
        }
        .scan-result-detail.severe {
            background-color: #f8d7da;
            border-left-color: #dc3545;
        }
        .scan-result-detail.general {
            background-color: #fff3cd;
            border-left-color: #ffc107;
        }
        .scan-result-content {
            padding: 8px 12px;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            font-size: 12px;
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
            max-width: 600px;
            white-space: pre-wrap;
        }
        .scan-result-suggestion {
            color: #6c757d;
            font-style: italic;
            max-width: 600px;
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
                    console.log(...args);
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
            // Expandable context logic
            const fileContents = document.getElementById('new-file-contents');
            if (fileContents) {
                const fileContentData = JSON.parse(fileContents.textContent);
                document.querySelectorAll('.expand-icon').forEach(function(btn) {
                    btn.addEventListener('click', function() {
                        const tr = btn.closest('tr');
                        const table = btn.closest('table');
                        const filename = table.getAttribute('data-filename');
                        const lines = fileContentData[filename] || [];
                        let expandType = btn.getAttribute('data-expand');
                        let contextStart = parseInt(btn.getAttribute('data-context-start'));
                        let contextEnd = parseInt(btn.getAttribute('data-context-end'));
                        
                        // Handle 10-line expansion
                        if (expandType === 'above-10') {
                            contextStart = Math.max(contextStart, contextEnd - 9);
                        } else if (expandType === 'below-10') {
                            contextEnd = Math.min(contextEnd, contextStart + 9);
                        }
                        
                        // Insert the context lines, but only if not already present
                        gitDiffLog(`===== EXPAND BUTTON CLICKED =====`);
                        gitDiffLog(`Expand type: ${expandType}`);
                        gitDiffLog(`Context range: ${contextStart} to ${contextEnd}`);
                        
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
                        for (let ln = contextStart; ln <= contextEnd; ++ln) {
                            if (!visibleLines.has(ln)) {
                                let content = lines[ln - 1] || '';
                                linesToInsert.push({lineNum: ln, content: content});
                            }
                        }
                        
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
                        linesToInsert.forEach(function(lineInfo, index) {
                            let newRow = document.createElement('tr');
                            newRow.className = 'diff-context expanded-context';
                            newRow.innerHTML = `<td class='diff-sign'>&nbsp;</td><td class='diff-line-num'></td><td class='diff-line-num'>${lineInfo.lineNum}</td><td class='diff-line-content'>${escapeHtml(lineInfo.content)}</td>`;
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
        html_parts = ['<div class="scan-results-list">']
        
        for result in scan_results:
            severity_class = 'severe' if result['严重程度'] == '严重' else ''
            safe_filename = result['文件名'].replace('/', '-').replace('\\', '-').replace('.', '-')
            jump_id = f"scanresult-{safe_filename}-{result['行号']}"
            issue_count = result.get('问题数量', 1)
            count_text = f" ({issue_count} issues)" if issue_count > 1 else ""
            html_parts.append(f'''
                <div class="scan-result-item {severity_class}" data-line="{result['行号']}" data-jump="{jump_id}">
                    <div class="file-name">文件名：{html.escape(result['文件名'])}</div>
                    <div class="line-number">行号： {result['行号']}{count_text}</div>
                    <div class="description">{html.escape(result['问题描述'])}</div>
                    <div class="suggestion">{html.escape(result['修改意见'])}</div>
                </div>
''')
        
        html_parts.append('</div>')
        return '\n'.join(html_parts) 