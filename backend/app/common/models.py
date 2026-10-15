from bson import ObjectId

from app.common.exceptions import BadRequestError


def to_object_id(id_str: str) -> ObjectId:
    """Turn a string into an ObjectId, or raise a 400."""
    if not ObjectId.is_valid(id_str):
        raise BadRequestError(f"Invalid ID: {id_str}")
    return ObjectId(id_str)


def serialize_doc(doc: dict) -> dict:
    """Convert a MongoDB document's _id from ObjectId to string 'id' field."""
    if doc is None:
        return None
    from datetime import datetime
    doc["id"] = str(doc.pop("_id"))
    # Convert ObjectId and datetime fields to strings
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            doc[key] = str(value)
        elif isinstance(value, datetime):
            doc[key] = value.isoformat()
        elif isinstance(value, list):
            doc[key] = [
                str(item) if isinstance(item, ObjectId) else item
                for item in value
            ]
    return doc


def serialize_docs(docs: list[dict]) -> list[dict]:
    """Serialize a list of MongoDB documents."""
    return [serialize_doc(doc) for doc in docs]
