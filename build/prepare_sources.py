#!/usr/bin/env python3
"""
Source Code Preprocessor
Strips comments, docstrings, and unnecessary whitespace from Python files
while preserving functionality
"""

import os
import sys
import ast
import astor
from pathlib import Path
from typing import List, Set


class DocstringRemover(ast.NodeTransformer):
    """AST transformer to remove docstrings while preserving code"""

    def visit_Module(self, node):
        # Remove module-level docstring
        if (node.body and isinstance(node.body[0], ast.Expr) and
                isinstance(node.body[0].value, (ast.Str, ast.Constant))):
            node.body = node.body[1:]
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node):
        # Remove function docstring
        if (node.body and isinstance(node.body[0], ast.Expr) and
                isinstance(node.body[0].value, (ast.Str, ast.Constant))):
            node.body = node.body[1:]
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        # Remove async function docstring
        if (node.body and isinstance(node.body[0], ast.Expr) and
                isinstance(node.body[0].value, (ast.Str, ast.Constant))):
            node.body = node.body[1:]
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node):
        # Remove class docstring
        if (node.body and isinstance(node.body[0], ast.Expr) and
                isinstance(node.body[0].value, (ast.Str, ast.Constant))):
            node.body = node.body[1:]
        self.generic_visit(node)
        return node


def strip_python_file(input_path: Path, output_path: Path, preserve_signatures: bool = True) -> bool:
    """
    Strip comments and docstrings from a Python file

    Args:
        input_path: Source file path
        output_path: Destination file path
        preserve_signatures: Keep function signatures for FastAPI routing

    Returns:
        True if successful, False otherwise
    """
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            source_code = f.read()

        # Parse the source code
        tree = ast.parse(source_code)

        # Remove docstrings
        remover = DocstringRemover()
        tree = remover.visit(tree)

        # Convert back to code
        stripped_code = astor.to_source(tree)

        # Write to output file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(stripped_code)

        return True

    except SyntaxError as e:
        print(f"  ⚠️  Syntax error in {input_path}: {e}")
        # Copy original file if parsing fails
        import shutil
        shutil.copy2(input_path, output_path)
        return False
    except Exception as e:
        print(f"  ❌ Error processing {input_path}: {e}")
        return False


def process_directory(
    source_dir: Path,
    output_dir: Path,
    exclude_patterns: Set[str] = None
) -> tuple:
    """
    Process all Python files in directory

    Args:
        source_dir: Source directory
        output_dir: Output directory
        exclude_patterns: Set of patterns to exclude

    Returns:
        Tuple of (processed_count, failed_count)
    """
    if exclude_patterns is None:
        exclude_patterns = {
            '__pycache__',
            '.git',
            '.pytest_cache',
            'build',
            'dist',
            '*.egg-info'
        }

    processed = 0
    failed = 0

    print(f"\n📦 Processing Python files:")
    print(f"  Source: {source_dir}")
    print(f"  Output: {output_dir}")
    print()

    for py_file in source_dir.rglob('*.py'):
        # Check if file should be excluded
        if any(pattern in str(py_file) for pattern in exclude_patterns):
            continue

        # Calculate relative path and output path
        rel_path = py_file.relative_to(source_dir)
        out_file = output_dir / rel_path

        print(f"  Processing: {rel_path}...", end='  ')

        if strip_python_file(py_file, out_file):
            print("✓")
            processed += 1
        else:
            print("⚠️  (copied original)")
            failed += 1

    return processed, failed


def copy_non_python_files(source_dir: Path, output_dir: Path, extensions: List[str]) -> int:
    """
    Copy non-Python files (like .tsv, .html, .css, .js)

    Args:
        source_dir: Source directory
        output_dir: Output directory
        extensions: List of file extensions to copy

    Returns:
        Number of files copied
    """
    import shutil
    copied = 0

    print(f"\n📄 Copying non-Python files:")

    for ext in extensions:
        for file_path in source_dir.rglob(f'*{ext}'):
            # Skip __pycache__ and other build artifacts
            if '__pycache__' in str(file_path) or '.git' in str(file_path):
                continue

            rel_path = file_path.relative_to(source_dir)
            out_file = output_dir / rel_path

            out_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, out_file)

            print(f"  Copied: {rel_path}")
            copied += 1

    return copied


def main():
    """Main entry point"""
    if len(sys.argv) < 3:
        print("Usage: python prepare_sources.py <source_dir> <output_dir>")
        sys.exit(1)

    source_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    if not source_dir.exists():
        print(f"❌ Source directory not found: {source_dir}")
        sys.exit(1)

    print("=" * 70)
    print("LoanPilot Source Code Preprocessor")
    print("=" * 70)

    # Process Python files
    processed, failed = process_directory(
        source_dir,
        output_dir,
        exclude_patterns={'__pycache__', '.git', 'tests', 'test_', '_test', 'build'}
    )

    # Copy non-Python files
    non_python_extensions = ['.tsv', '.html', '.css', '.js', '.json']
    copied = copy_non_python_files(source_dir, output_dir, non_python_extensions)

    # Summary
    print()
    print("=" * 70)
    print("Summary:")
    print(f"  Python files processed: {processed}")
    print(f"  Python files failed: {failed}")
    print(f"  Non-Python files copied: {copied}")
    print("=" * 70)

    if failed > 0:
        print(f"\n⚠️  Warning: {failed} files failed processing (originals copied)")

    print("\n✅ Source preparation complete!")


if __name__ == "__main__":
    main()
