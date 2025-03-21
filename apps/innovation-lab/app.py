from flask import Flask, render_template_string
import mysql.connector
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/")
def index():
    host = os.getenv("MYSQL_HOST")
    user = os.getenv("MYSQL_USER")
    password = os.getenv("MYSQL_PASSWORD")
    database = os.getenv("MYSQL_DATABASE")

    html = """
    <h1>Simple Web Application</h1>
    <h2>Attempting MySQL Connection...</h2>
    """

    status_code = 200  # Default status code

    try:
        logger.info(f"Attempting to connect to MySQL database at {host}")
        conn = mysql.connector.connect(
            host=host, user=user, password=password, database=database
        )
        if conn.is_connected():
            logger.info("Successfully connected to MySQL database")
            html += """
            <div style='color: green; background: #e8f5e9; padding: 10px; border-radius: 5px;'>
            <strong>Connected successfully to MySQL!</strong></div>
            """
            conn.close()
        else:
            status_code = 500
            logger.error(
                "Database Connection Error: Could not establish a valid connection to the database."
            )
            html += """
            <div style='color: #721c24; background: #f8d7da; padding: 10px; border-radius: 5px;'>
            <strong>Database Connection Error:</strong><br/>
            Could not establish a valid connection to the database.</div>
            """
    except Exception as e:
        status_code = 500
        logger.error(
            f"Database Connection Error: Could not connect to MySQL database on '{host}'. Error: {str(e)}"
        )
        html += f"""
        <div style='color: #721c24; background: #f8d7da; padding: 10px; border-radius: 5px;'>
        <strong>Database Connection Error:</strong><br/>
        Could not connect to MySQL database on '{host}'.<br/>
        Error: {str(e)}</div>
        """

    return render_template_string(html), status_code


if __name__ == "__main__":
    logger.info("Starting Flask application on port 80")
    app.run(host="0.0.0.0", port=80)
