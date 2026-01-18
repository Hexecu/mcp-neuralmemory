"""
Utility functions for the KG-MCP server.
"""

import json
from datetime import datetime, date, time
from typing import Any, Dict, List, Union


def serialize_neo4j_value(value: Any) -> Any:
    """
    Recursively serialize Neo4j values to JSON-compatible types.
    
    Handles:
    - neo4j.time.DateTime -> ISO string
    - neo4j.time.Date -> ISO string  
    - neo4j.time.Time -> ISO string
    - neo4j.time.Duration -> dict
    - neo4j.spatial.Point -> dict
    - nested dicts and lists
    """
    if value is None:
        return None
    
    # Handle Neo4j DateTime types
    type_name = type(value).__name__
    module_name = type(value).__module__
    
    if module_name.startswith('neo4j'):
        # Neo4j DateTime
        if type_name == 'DateTime':
            return value.isoformat()
        # Neo4j Date
        elif type_name == 'Date':
            return value.isoformat()
        # Neo4j Time
        elif type_name == 'Time':
            return value.isoformat()
        # Neo4j Duration
        elif type_name == 'Duration':
            return {
                'months': value.months,
                'days': value.days,
                'seconds': value.seconds,
                'nanoseconds': value.nanoseconds,
            }
        # Neo4j Point
        elif type_name == 'Point':
            return {
                'srid': value.srid,
                'x': value.x,
                'y': value.y,
                'z': getattr(value, 'z', None),
            }
        # Other Neo4j types - convert to string
        else:
            return str(value)
    
    # Handle Python datetime types
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    
    # Handle dict - recursively serialize
    if isinstance(value, dict):
        return {k: serialize_neo4j_value(v) for k, v in value.items()}
    
    # Handle list - recursively serialize
    if isinstance(value, (list, tuple)):
        return [serialize_neo4j_value(v) for v in value]
    
    # Handle sets
    if isinstance(value, set):
        return [serialize_neo4j_value(v) for v in value]
    
    # Handle bytes
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='replace')
    
    # Return primitives as-is
    return value


def serialize_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize a complete response dictionary for JSON output.
    
    Use this to wrap tool responses before returning.
    """
    return serialize_neo4j_value(data)


class Neo4jJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Neo4j types."""
    
    def default(self, obj):
        return serialize_neo4j_value(obj)
