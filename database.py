import sqlite3
from datetime import datetime, timedelta

DATABASE_NAME = 'calendar.db'

def get_db_connection():
    """Create and return a database connection."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with the events table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if old schema exists and migrate if needed
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
    table_exists = cursor.fetchone()
    
    if table_exists:
        # Check if we need to migrate from old schema
        cursor.execute("PRAGMA table_info(events)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'date' in columns and 'start_datetime' not in columns:
            # Migrate old schema to new schema
            migrate_schema(conn)
    else:
        # Create new schema
        cursor.execute('''
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_datetime TEXT NOT NULL,
                end_datetime TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                tag TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    
    # Create tags table if it doesn't exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tags'")
    tags_table_exists = cursor.fetchone()
    
    if not tags_table_exists:
        cursor.execute('''
            CREATE TABLE tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT NOT NULL,
                order_index INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        
        # Initialize default tags or migrate from JSON
        init_default_tags(conn)
    
    conn.close()

def init_default_tags(conn):
    """Initialize tags table with defaults or migrate from tags.json."""
    import json
    import os
    
    cursor = conn.cursor()
    
    # Check if tags.json exists
    tags_file = os.path.join(os.path.dirname(__file__), 'tags.json')
    
    if os.path.exists(tags_file):
        # Migrate from JSON
        try:
            with open(tags_file, 'r') as f:
                data = json.load(f)
                tags = data.get('tags', [])
                
                for tag in tags:
                    cursor.execute(
                        'INSERT INTO tags (name, color, order_index) VALUES (?, ?, ?)',
                        (tag['name'], tag['color'], tag.get('order', 0))
                    )
                conn.commit()
                print(f"Migrated {len(tags)} tags from tags.json to database")
        except Exception as e:
            print(f"Error migrating tags from JSON: {e}")
            conn.rollback()
            # Fall back to default tags
            _create_default_tags(cursor, conn)
    else:
        # Create default tags
        _create_default_tags(cursor, conn)

def _create_default_tags(cursor, conn):
    """Helper to create default tags in database."""
    default_tags = [
        {"name": "Work", "color": "#007bff", "order": 1},
        {"name": "Personal", "color": "#28a745", "order": 2},
        {"name": "Social", "color": "#ffc107", "order": 3},
        {"name": "Important", "color": "#dc3545", "order": 4}
    ]
    
    for tag in default_tags:
        cursor.execute(
            'INSERT INTO tags (name, color, order_index) VALUES (?, ?, ?)',
            (tag['name'], tag['color'], tag['order'])
        )
    conn.commit()
    print(f"Created {len(default_tags)} default tags in database")

def migrate_schema(conn):
    """Migrate from old schema (date, time) to new schema (start_datetime, end_datetime)."""
    cursor = conn.cursor()
    
    # Create new table with updated schema
    cursor.execute('''
        CREATE TABLE events_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_datetime TEXT NOT NULL,
            end_datetime TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            tag TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Migrate existing data
    cursor.execute('SELECT id, date, time, title, description, created_at FROM events')
    old_events = cursor.fetchall()
    
    for event in old_events:
        event_id, date, time, title, description, created_at = event
        
        # Convert old format to new format
        if time:
            # Parse time and create start_datetime
            start_datetime = f"{date} {time}:00"
            # Default to 1 hour duration
            start_dt = datetime.strptime(start_datetime, '%Y-%m-%d %H:%M:%S')
            end_dt = start_dt + timedelta(hours=1)
            end_datetime = end_dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            # All-day event: 9 AM to 5 PM
            start_datetime = f"{date} 09:00:00"
            end_datetime = f"{date} 17:00:00"
        
        cursor.execute('''
            INSERT INTO events_new (id, start_datetime, end_datetime, title, description, tag, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (event_id, start_datetime, end_datetime, title, description, None, created_at))
    
    # Drop old table and rename new table
    cursor.execute('DROP TABLE events')
    cursor.execute('ALTER TABLE events_new RENAME TO events')
    
    conn.commit()

def get_events_by_date(date):
    """Get all events for a specific date (including multi-day events that overlap this date)."""
    conn = get_db_connection()
    
    # Get events where the date falls between start and end datetime
    # We need to consider events that start on this day, end on this day, or span across this day
    date_start = f"{date} 00:00:00"
    date_end = f"{date} 23:59:59"
    
    events = conn.execute('''
        SELECT * FROM events 
        WHERE (start_datetime <= ? AND end_datetime >= ?)
        OR (DATE(start_datetime) = ?)
        OR (DATE(end_datetime) = ?)
        ORDER BY start_datetime
    ''', (date_end, date_start, date, date)).fetchall()
    
    conn.close()
    return events

def add_event(start_datetime, end_datetime, title, description='', tag=''):
    """Add a new event to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO events (start_datetime, end_datetime, title, description, tag) VALUES (?, ?, ?, ?, ?)',
        (start_datetime, end_datetime, title, description, tag)
    )
    conn.commit()
    event_id = cursor.lastrowid
    conn.close()
    return event_id

def update_event(event_id, start_datetime, end_datetime, title, description='', tag=''):
    """Update an existing event."""
    conn = get_db_connection()
    conn.execute(
        'UPDATE events SET start_datetime = ?, end_datetime = ?, title = ?, description = ?, tag = ? WHERE id = ?',
        (start_datetime, end_datetime, title, description, tag, event_id)
    )
    conn.commit()
    conn.close()

def delete_event(event_id):
    """Delete an event by ID."""
    conn = get_db_connection()
    conn.execute('DELETE FROM events WHERE id = ?', (event_id,))
    conn.commit()
    conn.close()

def bulk_add_events(events, tag=''):
    """
    Add multiple events to the database in a single transaction.
    
    Args:
        events: List of event dictionaries with keys:
                - title: Event title
                - description: Event description (optional)
                - start_datetime: Start datetime string (YYYY-MM-DD HH:MM:SS)
                - end_datetime: End datetime string (YYYY-MM-DD HH:MM:SS)
        tag: Tag to apply to all events (optional)
        
    Returns:
        int: Number of events successfully imported
    """
    if not events:
        return 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    imported_count = 0
    try:
        for event in events:
            title = event.get('title', '(no title)')
            description = event.get('description', '')
            start_datetime = event.get('start_datetime')
            end_datetime = event.get('end_datetime')
            
            if start_datetime and end_datetime:
                cursor.execute(
                    'INSERT INTO events (start_datetime, end_datetime, title, description, tag) VALUES (?, ?, ?, ?, ?)',
                    (start_datetime, end_datetime, title, description, tag)
                )
                imported_count += 1
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
    
    return imported_count


def get_events_by_tag(tag_name):
    """Get all events with a specific tag"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM events WHERE tag = ?', (tag_name,))
    events = cursor.fetchall()
    conn.close()
    return [dict(event) for event in events]


def get_tag_hours_for_week(start_date, end_date):
    """Get cumulative hours per tag for each day in a week.
    
    Handles multi-day events by clipping to day boundaries.
    Handles overlapping events (can result in >24 hours per day).
    
    Args:
        start_date: Week start date string 'YYYY-MM-DD'
        end_date: Week end date string 'YYYY-MM-DD'
    
    Returns:
        dict: {date_str: {tag: hours}}
    """
    from datetime import datetime, timedelta
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all events that overlap with the week
    cursor.execute('''
        SELECT id, start_datetime, end_datetime, tag
        FROM events
        WHERE start_datetime < ? AND end_datetime > ?
        ORDER BY start_datetime
    ''', (end_date, start_date))
    
    events = cursor.fetchall()
    conn.close()
    
    # Initialize result dict
    result = {}
    current_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    while current_date < end_date_dt:
        date_str = current_date.strftime('%Y-%m-%d')
        result[date_str] = {}
        current_date += timedelta(days=1)
    
    # Process each event
    for event in events:
        start_dt = datetime.strptime(event['start_datetime'], '%Y-%m-%d %H:%M:%S')
        end_dt = datetime.strptime(event['end_datetime'], '%Y-%m-%d %H:%M:%S')
        tag = event['tag'] if event['tag'] else 'Untagged'
        
        # Iterate through each day this event spans
        current_day = datetime.strptime(start_date, '%Y-%m-%d')
        while current_day < end_date_dt:
            day_start = datetime.combine(current_day, datetime.min.time())
            day_end = datetime.combine(current_day, datetime.max.time())
            
            # Check if event overlaps with this day
            if start_dt <= day_end and end_dt >= day_start:
                # Clip event to day boundaries
                clipped_start = max(start_dt, day_start)
                clipped_end = min(end_dt, day_end)
                
                # Calculate duration in hours
                duration_seconds = (clipped_end - clipped_start).total_seconds()
                duration_hours = duration_seconds / 3600.0
                
                # Add to result
                date_str = current_day.strftime('%Y-%m-%d')
                if tag not in result[date_str]:
                    result[date_str][tag] = 0
                result[date_str][tag] += duration_hours
            
            current_day += timedelta(days=1)
    
    return result


# Tag Management Functions

def get_all_tags():
    """Get all tags ordered by order_index."""
    conn = get_db_connection()
    tags = conn.execute('SELECT * FROM tags ORDER BY order_index').fetchall()
    conn.close()
    return [dict(tag) for tag in tags]

def add_tag(name, color, order_index=None):
    """Add a new tag."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # If no order specified, append to end
    if order_index is None:
        cursor.execute('SELECT MAX(order_index) FROM tags')
        max_order = cursor.fetchone()[0]
        order_index = (max_order or 0) + 1
    
    try:
        cursor.execute(
            'INSERT INTO tags (name, color, order_index) VALUES (?, ?, ?)',
            (name, color, order_index)
        )
        conn.commit()
        tag_id = cursor.lastrowid
        conn.close()
        return tag_id
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError(f"Tag '{name}' already exists")

def update_tag(tag_id, name, color):
    """Update a tag's name and color. If name changes, update all events with the old tag."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get old tag name
    cursor.execute('SELECT name FROM tags WHERE id = ?', (tag_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        raise ValueError(f"Tag with id {tag_id} not found")
    
    old_name = result[0]
    
    try:
        # Update tag
        cursor.execute(
            'UPDATE tags SET name = ?, color = ? WHERE id = ?',
            (name, color, tag_id)
        )
        
        # If name changed, update all events with the old tag name
        if old_name != name:
            cursor.execute(
                'UPDATE events SET tag = ? WHERE tag = ?',
                (name, old_name)
            )
        
        conn.commit()
        conn.close()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError(f"Tag '{name}' already exists")

def delete_tag(tag_id):
    """Delete a tag by ID. Sets events using this tag to None."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get tag name and count events using it
    cursor.execute('SELECT name FROM tags WHERE id = ?', (tag_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return {'success': False, 'error': 'Tag not found'}
    
    tag_name = result[0]
    cursor.execute('SELECT COUNT(*) FROM events WHERE tag = ?', (tag_name,))
    event_count = cursor.fetchone()[0]
    
    # Set events using this tag to None
    if event_count > 0:
        cursor.execute('UPDATE events SET tag = NULL WHERE tag = ?', (tag_name,))
    
    # Delete the tag
    cursor.execute('DELETE FROM tags WHERE id = ?', (tag_id,))
    conn.commit()
    conn.close()
    return {'success': True, 'event_count': event_count}

def reorder_tags(tag_ids):
    """Reorder tags. tag_ids is a list of tag IDs in the desired order."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for index, tag_id in enumerate(tag_ids):
        cursor.execute(
            'UPDATE tags SET order_index = ? WHERE id = ?',
            (index + 1, tag_id)
        )
    
    conn.commit()
    conn.close()


# Initialize the database when the module is imported
init_db()
