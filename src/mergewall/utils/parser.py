"""Code parsing utilities using tree-sitter."""

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CodeStructure:
    """Parsed structure of a code file."""
    functions: list[str]
    classes: list[str]
    imports: list[str]
    language: str


# File extension → language name mapping
EXT_LANG: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c_header",
    ".hpp": "cpp_header",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
}

SUPPORTED_EXTENSIONS: list[str] = list(EXT_LANG.keys())


def _detect_language(file_path: str) -> str:
    """Detect language from file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    return EXT_LANG.get(ext, "python")


def parse_code(code: str, language: str = "python", file_path: str = "") -> CodeStructure:
    """Parse code to extract its structure.

    Uses tree-sitter for multi-language AST parsing.
    Falls back to regex-based parsing if tree-sitter is not available.

    If *language* is the default "python" and *file_path* is provided,
    the language is auto-detected from the file extension.
    """
    if language == "python" and file_path:
        language = _detect_language(file_path)
    try:
        return _parse_with_tree_sitter(code, language)
    except Exception:
        return _parse_with_regex(code, language)


def _parse_with_tree_sitter(code: str, language: str) -> CodeStructure:
    """Parse code using tree-sitter for accurate AST analysis."""
    if language != "python":
        logger.debug("No tree-sitter grammar for %s, using regex fallback", language)
        return _parse_with_regex(code, language)

    import tree_sitter_python as tspython
    from tree_sitter import Language, Parser

    parser = Parser(Language(tspython.language()))
    tree = parser.parse(code.encode())

    functions = []
    classes = []
    imports = []

    def walk(node):
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                functions.append(name_node.text.decode())
        elif node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                classes.append(name_node.text.decode())
        elif node.type in ("import_statement", "import_from_statement"):
            imports.append(node.text.decode())

        for child in node.children:
            walk(child)

    walk(tree.root_node)

    return CodeStructure(
        functions=functions,
        classes=classes,
        imports=imports,
        language=language,
    )


def _parse_with_regex(code: str, language: str) -> CodeStructure:
    """Fallback regex-based parsing with language-aware patterns."""
    import re

    # Language-specific regex patterns: (func_re, class_re, import_re)
    _PATTERNS: dict[str, tuple[str, str, str]] = {
        "python": (
            r"def\s+(\w+)\s*\(",
            r"class\s+(\w+)",
            r"^(?:import|from)\s+.+$",
        ),
        "javascript": (
            r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:function|async\s+function|\([^)]*\)\s*=>|\w+\s*=>))",
            r"class\s+(\w+)",
            r"^(?:import\s+.+|const\s+.+\s*=\s*require\s*\(.+\))",
        ),
        "typescript": (
            r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*(?::\s*\w+)?\s*=\s*(?:function|async\s+function|\([^)]*\)\s*=>|\w+\s*=>))",
            r"(?:class|interface|type)\s+(\w+)",
            r"^(?:import\s+.+|export\s+(?:default\s+)?(?:class|function|const|let|var)\s+)",
        ),
        "go": (
            r"func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(",
            r"(?:type\s+(\w+)\s+struct)",
            r'^import\s+(?:"[^"]+"|\([\s\S]*?\))',
        ),
        "rust": (
            r"(?:fn\s+(\w+))",
            r"(?:struct|enum|trait)\s+(\w+)",
            r"^use\s+.+;",
        ),
        "java": (
            r"(?:public|private|protected)?\s*(?:static\s+)?(?:\w+\s+)+(\w+)\s*\([^)]*\)\s*(?:throws\s+\w+(?:\s*,\s*\w+)*)?\s*\{",
            r"(?:class|interface|enum)\s+(\w+)",
            r"^import\s+(?:static\s+)?[\w.]+\s*;",
        ),
        "c": (
            r"(?:\w+\s+)+(\w+)\s*\([^)]*\)\s*\{",
            r"(?:struct|enum)\s+(\w+)",
            r"^#include\s+[<\"].+[>\"]",
        ),
        "cpp": (
            r"(?:\w+\s+)+(\w+)\s*\([^)]*\)\s*(?:const\s*)?\{",
            r"(?:class|struct|enum)\s+(\w+)",
            r"^#include\s+[<\"].+[>\"]",
        ),
        "c_header": (
            r"(?:\w+\s+)+(\w+)\s*\([^)]*\)\s*;",
            r"(?:struct|enum|typedef)\s+(\w+)",
            r"^#include\s+[<\"].+[>\"]",
        ),
        "cpp_header": (
            r"(?:\w+\s+)+(\w+)\s*\([^)]*\)\s*(?:const\s*)?;",
            r"(?:class|struct|enum)\s+(\w+)",
            r"^#include\s+[<\"].+[>\"]",
        ),
        "ruby": (
            r"def\s+(\w+[!?]?)",
            r"class\s+(\w+)",
            r"^(?:require|require_relative)\s+",
        ),
        "php": (
            r"function\s+(\w+)\s*\(",
            r"class\s+(\w+)",
            r"^use\s+[\w\\]+\s*;",
        ),
        "swift": (
            r"func\s+(\w+)\s*\(",
            r"(?:class|struct|enum|protocol)\s+(\w+)",
            r"^import\s+\w+",
        ),
        "kotlin": (
            r"fun\s+(\w+)\s*(?:<[^>]*>)?\s*\(",
            r"(?:class|object|interface|enum)\s+(\w+)",
            r"^import\s+[\w.]+\s*$",
        ),
    }

    func_re, class_re, import_re = _PATTERNS.get(language, _PATTERNS["python"])

    # Extract functions — handle patterns with multiple capture groups
    func_matches = re.findall(func_re, code, re.MULTILINE)
    functions = [m for group in func_matches for m in (group if isinstance(group, tuple) else (group,)) if m]

    classes = re.findall(class_re, code, re.MULTILINE)
    imports = re.findall(import_re, code, re.MULTILINE)

    return CodeStructure(
        functions=functions,
        classes=classes,
        imports=imports,
        language=language,
    )
