from flask import Flask

app = Flask(__name__)


@app.route("/status")  # Note: Health check will look for /health instead
def status():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
