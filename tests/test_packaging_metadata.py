import ast
from pathlib import Path
import unittest


PROJECT_DIR = Path(__file__).resolve().parents[1]


def read_setup_install_requires():
    setup_tree = ast.parse((PROJECT_DIR / "setup.py").read_text())
    module_constants = {}

    for node in setup_tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    module_constants[target.id] = ast.literal_eval(node.value)

    for node in ast.walk(setup_tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "setup":
            continue
        for keyword in node.keywords:
            if keyword.arg != "install_requires":
                continue
            if isinstance(keyword.value, ast.Name):
                return module_constants[keyword.value.id]
            return ast.literal_eval(keyword.value)

    return []


class PackagingMetadataTest(unittest.TestCase):
    def test_setup_py_keeps_legacy_build_dependencies(self):
        self.assertIn("websocket-client>=1.6", read_setup_install_requires())

    def test_pyproject_uses_setup_py_dependencies(self):
        pyproject = (PROJECT_DIR / "pyproject.toml").read_text()

        self.assertIn('dynamic = ["dependencies"]', pyproject)
        self.assertNotIn("dependencies = [", pyproject)

    def test_cmake_rebuilds_when_python_package_metadata_changes(self):
        cmake_lists = (PROJECT_DIR / "CMakeLists.txt").read_text()

        self.assertIn('"${CMAKE_CURRENT_SOURCE_DIR}/pyproject.toml"', cmake_lists)
        self.assertIn('"${CMAKE_CURRENT_SOURCE_DIR}/MANIFEST.in"', cmake_lists)