"""Regression coverage for deterministic SQLite test-connection cleanup."""

import ast
from pathlib import Path
import sqlite3
import tempfile
import unittest
from contextlib import closing


TESTS_DIR = Path(__file__).resolve().parent


def _is_sqlite_connect_call(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "connect"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "sqlite3"
    )


class TestSQLiteTestConnectionCleanup(unittest.TestCase):
    def test_sqlite_connections_in_tests_are_closed_deterministically(self):
        offenders = []
        for path in sorted(TESTS_DIR.glob("test_*.py")):
            if path == Path(__file__):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.With):
                    continue
                for item in node.items:
                    if _is_sqlite_connect_call(item.context_expr):
                        offenders.append(f"{path.name}:{node.lineno}")

        self.assertEqual(
            offenders,
            [],
            "SQLite test connections must use closing(sqlite3.connect(...)) "
            f"rather than the non-closing connection context manager: {offenders}",
        )

    def test_closing_releases_sqlite_handle_after_transaction(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "connection.db"
            connection = sqlite3.connect(path)
            with closing(connection) as connection, connection:
                connection.execute("CREATE TABLE probe (value INTEGER)")
                connection.execute("INSERT INTO probe VALUES (1)")

            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute("SELECT value FROM probe")

            with closing(sqlite3.connect(path)) as verification:
                self.assertEqual(verification.execute("SELECT value FROM probe").fetchone()[0], 1)
