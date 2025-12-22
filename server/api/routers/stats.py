from fastapi import APIRouter, HTTPException


router = APIRouter()


@router.get("/stats")
async def get_stats():
    """
    Return system statistics for the dashboard/timeline.
    """
    try:
        from server import main as main_module

        # Leverage existing stats logic or db
        stats = main_module.photo_search_engine.db.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeline")
async def get_timeline():
    """
    Return distribution of photos over time for the Sonic Timeline.
    Grouping by month for now.
    """
    try:
        from server import main as main_module

        # We need a method to get date stats.
        # photo_search_engine.db has get_stats() but that's summary.
        # We'll execute a raw query on the db for now until we extend MetadataDatabase.

        # Connect to db safely using the existing connection if available
        # The MetadataDatabase handles connection in __init__

        cursor = main_module.photo_search_engine.db.conn.cursor()

        # Query: Count photos per month
        # SQLite: strftime('%Y-%m', created_at)
        # Fix: Use COALESCE to ensure safety against nulls
        query = """
            SELECT strftime('%Y-%m', json_extract(metadata_json, '$.filesystem.created')) as month, COUNT(*) as count
            FROM metadata
            WHERE json_extract(metadata_json, '$.filesystem.created') IS NOT NULL
            GROUP BY month
            ORDER BY month ASC
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        timeline_data = [{"date": row[0], "count": row[1]} for row in rows]
        return {"timeline": timeline_data}

    except Exception as e:
        # Fallback if table doesn't exist or other error
        print(f"Timeline error: {e}")
        return {"timeline": []}
