# Git/SVN Review Page Generator

This tool generates static HTML review pages similar to Helix Swarm's interface, supporting both Git repositories and SVN working copies. It automatically detects the repository type and uses the appropriate generator.

## Features

- **Automatic Repository Detection**: Automatically detects whether the target is a Git repository or SVN working copy
- **Git Support**: Generate review pages for Git commits with full diff visualization
- **SVN Support**: Generate review pages for SVN revisions with full diff visualization  
- **Scan Results Integration**: Display code analysis results from JSON files alongside diffs
- **Interactive Interface**: File tree navigation, expandable context, and clickable scan results
- **Modern UI**: Clean, responsive interface similar to modern code review tools

## Requirements

- Python 3.6+
- Git (for Git repositories)
- SVN command line tools (for SVN repositories)

## Installation

No installation required. Just ensure you have Python 3.6+ and the required VCS tools (Git/SVN) installed.

## Usage

### Basic Usage

```bash
# Automatic detection - works for both Git and SVN
python parse_diff_generate_html.py /path/to/repository

# With specific commit/revision
python parse_diff_generate_html.py /path/to/repository --commit abc123

# With scan results
python parse_diff_generate_html.py /path/to/repository --scan-results /path/to/scan/results

# Generate multiple reviews
python parse_diff_generate_html.py /path/to/repository --num-commits 5
```

### Command Line Options

- `repo_path`: Path to the Git repository or SVN working copy
- `--output-dir, -o`: Output directory for generated HTML files (default: ./reviews)
- `--commit, -c`: Specific commit hash (Git) or revision number (SVN) to generate review for
- `--num-commits, -n`: Number of recent commits/revisions to generate reviews for (default: 1)
- `--template-dir, -t`: Directory containing custom templates
- `--scan-results, -s`: Directory containing scan results JSON files

### Examples

#### Git Repository
```bash
# Generate review for latest commit
python parse_diff_generate_html.py /path/to/git/repo

# Generate review for specific commit
python parse_diff_generate_html.py /path/to/git/repo --commit a1b2c3d4

# Generate reviews for last 3 commits with scan results
python parse_diff_generate_html.py /path/to/git/repo --num-commits 3 --scan-results ./scan_results
```

#### SVN Repository
```bash
# Generate review for latest revision
python parse_diff_generate_html.py /path/to/svn/working/copy

# Generate review for specific revision
python parse_diff_generate_html.py /path/to/svn/working/copy --commit 1234

# Generate reviews for last 5 revisions
python parse_diff_generate_html.py /path/to/svn/working/copy --num-commits 5
```

## Repository Detection

The tool automatically detects the repository type using the `is_git_or_svn()` function:

1. **Git Detection**:
   - Checks for `.git` directory
   - Attempts to run `git status`

2. **SVN Detection**:
   - Checks for `.svn` directory in current or parent directories
   - Attempts to run `svn info`

3. **Fallback**: If neither is detected, the tool reports an error

## Scan Results Format

The tool supports scan results in JSON format with the following structure:

```json
{
  "file": "path/to/file.cpp",
  "源码": "source code content...",
  "可能存在的问题": [
    {
      "行号范围": "100-105",
      "问题描述": "Potential null pointer dereference",
      "修改意见": "Add null check before use"
    }
  ],
  "肯定存在的问题": [
    {
      "行号范围": "150",
      "问题描述": "Memory leak detected",
      "修改意见": "Add proper cleanup"
    }
  ]
}
```

## Architecture

### Classes

- **GitCommitReviewGenerator**: Handles Git repositories
  - Uses `git` commands for commit info, diffs, and file lists
  - Generates review pages for Git commits

- **SVNRevisionReviewGenerator**: Handles SVN repositories  
  - Uses `svn` commands for revision info, diffs, and file lists
  - Generates review pages for SVN revisions

### Key Functions

- **is_git_or_svn(repo_path)**: Detects repository type
- **load_scan_results()**: Loads and processes scan result JSON files
- **parse_diff_to_html()**: Converts diffs to HTML with syntax highlighting
- **generate_review_page()**: Creates the main review HTML page

## Output

The tool generates:

- **index.html**: Main index page listing all generated reviews
- **review-{hash/revision}.html**: Individual review pages
- **assets/style.css**: Styling for the review pages
- **assets/script.js**: JavaScript for interactive features

## Differences Between Git and SVN

| Feature | Git | SVN |
|---------|-----|-----|
| Identifier | Commit hash (e.g., a1b2c3d4) | Revision number (e.g., r1234) |
| Commands | `git log`, `git diff`, etc. | `svn log`, `svn diff`, etc. |
| File paths | Repository relative | May include trunk/branches prefix |
| History | Distributed | Centralized |
| Output files | `review-{hash}.html` | `review-r{revision}.html` |

## Testing

Use the provided test script to verify repository detection:

```bash
python test_review_generator.py
```

## Limitations

### SVN Limitations
- Requires SVN command line tools
- Some diff features may vary compared to Git
- Repository URL construction may need adjustment for different SVN layouts

### General Limitations
- Large repositories may take time to process
- Scan results must follow the specific JSON format
- Binary files are not handled in diffs

## Troubleshooting

### Common Issues

1. **"Not a valid repository"**: Ensure the path points to a valid Git repo or SVN working copy
2. **SVN diff errors**: Check that SVN command line tools are installed and accessible
3. **Missing scan results**: Ensure scan result JSON files follow the expected format
4. **Permission errors**: Check write permissions for the output directory

### Debug Information

The tool prints debug information including:
- Repository type detection results
- SVN/Git command execution
- Scan result loading progress
- File processing status

## Contributing

Feel free to submit issues and enhancement requests. The tool is designed to be extensible for other VCS systems.

## License

This project is provided as-is for educational and internal use purposes.
