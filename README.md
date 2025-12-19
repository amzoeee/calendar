# Flask Calendar App

A simple, elegant Flask-based calendar application with daily view and persistent event storage.

## Setup

1. **Clone or navigate to this directory**

2. **Create a virtual environment (optional but recommended)**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

1. **Start the Flask development server**
   ```bash
   python app.py
   ```

2. **Open your browser**
   Navigate to: `http://localhost:5001`

3. **Start adding events!**
   - The app will automatically redirect to today's date
   - Use the navigation buttons to move between days
   - Click "Today" to jump back to the current date

## Data Persistence

All events are stored in a SQLite database file (`calendar.db`) which is created automatically when you first run the application. This database file persists between server restarts, so your events will always be there when you return!

## Event Tags and Customization

The application supports categorizing events with custom tags and colors.

1.  **Customize Tags**: You can define your own tags in `tags.json`. Each tag has a `name`, a HEX `color`, and an `order` for display:
    ```json
    {
        "tags": [
            {"name": "Work", "color": "#007bff", "order": 1},
            {"name": "Social", "color": "#ffc107", "order": 3}
        ]
    }
    ```
2.  **Auto-Generation**: To ensure the app works out of the box, `create_default_tags.py` automatically generates a default `tags.json` file if one doesn't exist when the server starts.

## Project Structure

```
calendar/
├── app.py              # Main Flask application
├── database.py         # Database operations and schema
├── create_default_tags.py # Default tag generation script
├── requirements.txt    # Python dependencies
├── templates/
│   └── daily.html     # Daily view template
├── static/
│   └── style.css      # Styling
└── calendar.db        # SQLite database (created on first run)
```

## Technologies Used

- **Flask** - Python web framework
- **SQLite** - Lightweight database for data persistence
- **HTML/CSS** - Frontend with modern styling
- **JavaScript** - Event editing functionality
