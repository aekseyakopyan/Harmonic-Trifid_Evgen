import aiosqlite
from contextlib import asynccontextmanager
from core.config import DB_PATH


@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        yield db


async def run_migrations():
    import glob
    import os
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    sql_files = sorted(glob.glob(os.path.join(migrations_dir, "*.sql")))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys=ON")
        for path in sql_files:
            with open(path) as f:
                sql = f.read()
            # Execute each statement individually so one failure doesn't block the rest
            for stmt in sql.split(";"):
                stmt = stmt.strip()
                if not stmt:
                    continue
                try:
                    await db.execute(stmt)
                    await db.commit()
                except Exception as e:
                    err = str(e).lower()
                    if "duplicate column" in err or "already exists" in err:
                        pass  # idempotent re-run
                    else:
                        print(f"  [migration] {os.path.basename(path)}: {e}")
    print("Migrations done")
