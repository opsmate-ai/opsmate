from flask import Flask
import mysql.connector
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/healthz")
def index():
    # ping mysql db
    try:
        conn = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE"),
            connect_timeout=5,
        )
        conn.ping(reconnect=False, attempts=1)
        conn.close()
        return "OK"
    except Exception as e:
        logger.error(f"Error connecting to MySQL: {e}")
        return "ERROR", 500


if __name__ == "__main__":
    logger.info("Starting Flask application on port 80")
    app.run(host="0.0.0.0", port=80)
