# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "fastapi",
#   "uvicorn",
# ]
# ///


import re
import sqlite3
import unicodedata
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# uv run searchpar.py


def grup(text: str) -> str:
    """
    Transforms Greek text to uppercase and removes special characters:
    - Converts to uppercase
    - Removes accent marks and other diacritics
    - Keeps only valid characters (Greek letters, Latin letters, numbers)

    Args:
        text: The Greek text to normalize

    Returns:
        The normalized text in uppercase without special characters
    """
    if not text:
        return ""

    text = text.upper()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^Α-Ω0-9A-Z\s]", "", text)
    text = re.sub(r"\s+", " ", text)  # Replace multiple spaces with a single space
    return text


class StorageSqlite:
    def __init__(self, db_path: str):
        self.connection = sqlite3.connect(db_path)
        self.connection.create_function("GRUP", 1, grup)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self.table_list = [row["param"] for row in self.get_table_names()]

    def get_table_names(self):
        """Get the list of tables in the database."""
        self.cursor.execute("SELECT param, description FROM meta")
        meta_data = self.cursor.fetchall()
        return meta_data

    def search(self, table: str, searchfor: str):
        """Search for parameters in the specified table."""
        if table not in self.table_list:
            raise ValueError(f"Table '{table}' does not exist in the database.")

        self.cursor.execute(
            f"SELECT code, description FROM {table} WHERE code LIKE ? OR GRUP(description) LIKE ?",
            (f"%{searchfor}%", f"%{grup(searchfor)}%"),
        )
        rows = self.cursor.fetchall()
        return rows

    def close(self):
        self.cursor.close()
        self.connection.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = StorageSqlite("ergani_parameters.db")
    print("Database started !!!")
    try:
        yield
    finally:
        app.state.db.close()
        print("Database closed !!!")


app = FastAPI(
    title="Ergani Parameter Tables API",
    version="0.1.1",
    lifespan=lifespan,
    description="API for searching parameters from the ERGANI database.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def search(table: str, searchfor: str):
    """Load parameters from the file according to the search term."""
    try:
        rows = app.state.db.search(table, searchfor)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

    return {
        "searchfor": searchfor,
        "code": table,
        "results": rows,
    }


@app.get("/tables")
async def get_tables():
    """Get the list of tables in the database."""
    try:
        tables = app.state.db.get_table_names()
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

    return {"tables": tables}


@app.get("/health/ping")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8040)
