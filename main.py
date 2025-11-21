import os
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Snippet

app = FastAPI(title="Anon Code Share API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Anon Code Share backend running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, "name") else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# Request/response models
class SnippetCreate(BaseModel):
    title: str
    filename: Optional[str] = None
    language: Optional[str] = None
    tags: Optional[List[str]] = None
    content: str


class SnippetOut(BaseModel):
    id: str
    title: str
    filename: Optional[str]
    language: Optional[str]
    tags: Optional[List[str]] = None
    content: str
    created_at: str


# Helpers
from bson import ObjectId


def serialize_snippet(doc) -> SnippetOut:
    return SnippetOut(
        id=str(doc.get("_id")),
        title=doc.get("title", "Untitled"),
        filename=doc.get("filename"),
        language=doc.get("language"),
        tags=doc.get("tags"),
        content=doc.get("content", ""),
        created_at=(doc.get("created_at") or datetime.now(timezone.utc)).isoformat(),
    )


@app.post("/api/snippets", response_model=SnippetOut)
def create_snippet(payload: SnippetCreate):
    try:
        # Validate via schema
        snippet = Snippet(**payload.model_dump())
        inserted_id = create_document("snippet", snippet)
        doc = db["snippet"].find_one({"_id": ObjectId(inserted_id)})
        return serialize_snippet(doc)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/snippets", response_model=List[SnippetOut])
def list_snippets(limit: int = 20):
    try:
        docs = get_documents("snippet", {}, limit=limit)
        return [serialize_snippet(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
