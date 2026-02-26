from __future__ import annotations

import sqlite3


class Cursor:
    def __init__(self, cursor):
        self._cursor = cursor

    async def fetchone(self):
        return self._cursor.fetchone()

    async def fetchall(self):
        return self._cursor.fetchall()


class Connection:
    def __init__(self, conn):
        self._conn = conn

    async def execute(self, sql, params=()):
        cur = self._conn.execute(sql, params)
        return Cursor(cur)

    async def commit(self):
        self._conn.commit()

    async def close(self):
        self._conn.close()


async def connect(path: str):
    conn = sqlite3.connect(path)
    return Connection(conn)
