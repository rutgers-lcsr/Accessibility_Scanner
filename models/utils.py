from sqlalchemy import or_
from typing import Any, Dict, Type
from sqlalchemy.orm import Query
from sqlalchemy.ext.declarative import DeclarativeMeta



def apply_filters(
    query: Query,
    model: Type[DeclarativeMeta],
    filters: Dict[str, Any]
) -> Query:
    for key, value in filters.items():
        column = getattr(model, key, None)
        if column is not None:
            if isinstance(value, str):
                query = query.filter(column.ilike(f"%{value}%"))
            else:
                query = query.filter(column == value)
    return query
