import ast
from pathlib import Path

RESEARCH_MODULES = (
    Path("src/zksato/video_ea.py"),
    Path("src/zksato/video_ea_runtime.py"),
)
FORBIDDEN_IMPORT_PREFIXES = (
    "zksato.broker",
    "zksato.service",
    "zksato.approvals",
    "settrade",
    "httpx",
    "requests",
)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


def test_video_ea_research_modules_have_no_execution_or_network_dependencies() -> None:
    for path in RESEARCH_MODULES:
        imports = _imports(path)
        for name in imports:
            assert not name.startswith(FORBIDDEN_IMPORT_PREFIXES), (path, name)


def test_video_ea_research_modules_do_not_expose_submit_or_execute_methods() -> None:
    for path in RESEARCH_MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert "submit" not in names
        assert "execute" not in names
        assert "place_order" not in names
        assert "send_order" not in names
