import re
import sqlite3 as sql
import datetime
import sys
import time
import threading
from typing import OrderedDict
from core.config import (
    stationCode, scaleCode, wagonNumber, wagonNumberAttachId, wagonAttachId2, wagonAttachId,
    scaleNumber, createdDate, LOG_PATH, sentAt, ID, identifier, num_count, backup_db_name,
    default_station_code, default_scale_code, log)


sourceId: str = "source_id"

_TBL_NAME_RE = re.compile(r"history_(\d{4})_(\d{2})")


def current_time() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _history_table_name() -> str:
    return "history_" + time.strftime("%Y_%m")


_BACKUP_COLUMNS = f"""
    {ID} INTEGER PRIMARY KEY AUTOINCREMENT,
    {wagonAttachId} TEXT DEFAULT '',
    {wagonAttachId2} TEXT DEFAULT '',
    {wagonNumberAttachId} TEXT DEFAULT '',
    {wagonNumber} TEXT,
    {scaleNumber} TEXT,
    {stationCode} TEXT DEFAULT '{default_station_code}',
    {scaleCode} TEXT DEFAULT '{default_scale_code}',
    {createdDate} TEXT
"""

_HISTORY_COLUMNS = f"""
    {ID} INTEGER PRIMARY KEY AUTOINCREMENT,
    {sourceId} INTEGER,
    {wagonAttachId} TEXT DEFAULT '',
    {wagonAttachId2} TEXT DEFAULT '',
    {wagonNumberAttachId} TEXT DEFAULT '',
    {wagonNumber} TEXT,
    {scaleNumber} TEXT,
    {stationCode} TEXT DEFAULT '{default_station_code}',
    {scaleCode} TEXT DEFAULT '{default_scale_code}',
    {createdDate} TEXT,
    {sentAt} TEXT DEFAULT 'Yuborilmagan'
"""


class BufferDB:

    def __init__(self):
        self._lock = threading.Lock()
        self.conn: sql.Connection = sql.connect(backup_db_name, check_same_thread=False)
        self.cursor: sql.Cursor = self.conn.cursor()
        self.table_name: str = "backup"
        self.history_table_name: str = _history_table_name()
        self._create_table()

    # ---- helpers ----

    def _execute(self, query: str, params: tuple = ()) -> sql.Cursor:
        with self._lock:
            result = self.cursor.execute(query, params)
            self.conn.commit()
            return result

    def _ensure_history_table(self) -> None:
        self.history_table_name = _history_table_name()
        with self._lock:
            self.cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
                (self.history_table_name,),
            )
            if self.cursor.fetchone() is None:
                self.cursor.execute(
                    f"CREATE TABLE IF NOT EXISTS {self.history_table_name} ({_HISTORY_COLUMNS})"
                )
                self.conn.commit()

    def _extract_fields(self, data: dict) -> tuple:
        return (
            data.get(wagonAttachId, ""),
            data.get(wagonAttachId2, ""),
            data.get(wagonNumberAttachId, ""),
            data.get(wagonNumber, identifier * num_count),
            data.get(scaleNumber, "0"),
            data.get(stationCode, default_station_code),
            data.get(scaleCode, default_scale_code),
            data.get(createdDate, current_time()),
        )

    # ---- init ----

    def _create_table(self) -> None:
        try:
            self._execute(
                f"CREATE TABLE IF NOT EXISTS {self.table_name} ({_BACKUP_COLUMNS})"
            )
            self._ensure_history_table()
        except Exception as err:
            log(message=f"[db.BufferDB.create_table] {err}")
            print(f"[db.BufferDB.create_table] {err}")
            sys.exit()

    # ---- CRUD ----

    def insert(self, data: dict) -> tuple[bool, str]:
        try:
            self._ensure_history_table()
            fields = self._extract_fields(data)
            (wagon_img, wagon_img2, wagon_id_img,
             wagon_num, scale_num, station, scale, created_at) = fields

            with self._lock:
                self.cursor.execute(f"""
                    INSERT INTO {self.table_name} (
                        {wagonAttachId}, {wagonAttachId2}, {wagonNumberAttachId},
                        {wagonNumber}, {scaleNumber}, {stationCode}, {scaleCode}, {createdDate}
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """, fields)
                source_id = self.cursor.lastrowid
                self.conn.commit()

                self.cursor.execute(f"""
                    INSERT INTO {self.history_table_name} (
                        {sourceId}, {wagonAttachId}, {wagonAttachId2}, {wagonNumberAttachId},
                        {wagonNumber}, {scaleNumber}, {stationCode}, {scaleCode}, {createdDate}
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (source_id, *fields))
                self.conn.commit()

            return True, ""
        except Exception as err:
            log(message=f"[db.BufferDB.insert] {err}")
            print(f"[db.BufferDB.insert] {err}")
            return False, str(err)

    def insert_history(self, data: dict) -> tuple[int | bool, str]:
        """Yangi tarix qatori qo'shadi. Muvaffaqiyatli bo'lsa haqiqiy DB ID ni qaytaradi."""
        try:
            self._ensure_history_table()
            fields = self._extract_fields(data)
            sent_at = data.get(sentAt, current_time())

            with self._lock:
                self.cursor.execute(f"""
                    INSERT INTO {self.history_table_name} (
                        {sourceId}, {wagonAttachId}, {wagonAttachId2}, {wagonNumberAttachId},
                        {wagonNumber}, {scaleNumber}, {stationCode}, {scaleCode},
                        {createdDate}, {sentAt}
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (0, *fields, sent_at))
                new_id = self.cursor.lastrowid
                self.conn.commit()

            return new_id, ""
        except Exception as err:
            log(message=f"[db.BufferDB.insert_history] {err}")
            print(f"[db.BufferDB.insert_history] {err}")
            return False, str(err)

    def get_all_history(self) -> tuple[dict, str]:
        try:
            with self._lock:
                self.cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'history_%' LIMIT 6;"
                )
                tables = [row[0] for row in self.cursor.fetchall()]

            months_dict: dict[str, list[dict]] = {}

            for tbl in tables:
                try:
                    with self._lock:
                        rows = self.cursor.execute(f"SELECT * FROM {tbl};").fetchall()
                    m = _TBL_NAME_RE.match(tbl)
                    if not rows:
                        if m:
                            month_key = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}"
                            months_dict[month_key] = []
                        continue

                    with self._lock:
                        columns = [desc[0] for desc in self.cursor.description]
                    rows_dicts = [dict(zip(columns, row)) for row in rows]

                    if m:
                        month_key = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}"
                    else:
                        month_key = tbl

                    months_dict.setdefault(month_key, [])
                    months_dict[month_key].extend(rows_dicts)

                except Exception as inner_err:
                    log(message=f"[db.get_all_history] failed read table {tbl}: {inner_err}")
                    continue

            for items in months_dict.values():
                try:
                    items.sort(key=lambda x: x.get(createdDate) or "")
                except Exception:
                    pass

            def _month_sort_key(kx: str):
                try:
                    y, mx = kx.split("-")
                    return int(y), int(mx)
                except Exception:
                    return 9999, 99

            ordered = OrderedDict()
            for k in sorted(months_dict.keys(), key=_month_sort_key):
                ordered[k] = months_dict[k]

            return ordered, ""
        except Exception as err:
            log(message=f"[db.BufferDB.get_all_history] {err}")
            print(f"[db.BufferDB.get_all_history] {err}")
            return {}, str(err)

    def get_all(self) -> tuple[list[dict], str]:
        try:
            with self._lock:
                rows = self.cursor.execute(f"SELECT * FROM {self.table_name}").fetchall()
                columns = [desc[0] for desc in self.cursor.description]
            return [dict(zip(columns, row)) for row in rows], ""
        except Exception as err:
            log(message=f"[db.BufferDB.get_all] {err}")
            print(f"[db.BufferDB.get_all] {err}")
            return [], str(err)

    def get_total(self) -> int:
        try:
            with self._lock:
                self.cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
                total = self.cursor.fetchone()[0]
            return total
        except Exception as err:
            log(message=f"[db.BufferDB.get_total] {err}")
            print(f"[db.BufferDB.get_total] {err}")
            return 0

    def delete(self, record_id: int | None) -> tuple[bool, str]:
        if record_id is None:
            return False, "id is required"
        try:
            with self._lock:
                self.cursor.execute(
                    f"DELETE FROM {self.table_name} WHERE {ID} = ?;", (record_id,)
                )
                self.conn.commit()
                sent_at = current_time()
                self.cursor.execute(
                    f"UPDATE {self.history_table_name} SET {sentAt} = ? WHERE {sourceId} = ?;",
                    (sent_at, record_id),
                )
                self.conn.commit()
            return True, ""
        except Exception as err:
            log(message=f"[db.BufferDB.delete] {err}")
            print(f"[db.BufferDB.delete] {err}")
            return False, str(err)

    def close(self):
        with self._lock:
            self.cursor.close()
            self.conn.close()
