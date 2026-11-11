from flask import Flask, render_template, request
import json
import queue

app = Flask(__name__)

# Keep a list of connected browser clients
listeners = []


@app.route("/webhook", methods=["POST"])
def webhook():
    # Receive the incoming JSON payload from Apprise or any webhook
    data = request.get_json(force=True, silent=True)
    if not data:
        return {"error": "No JSON provided"}, 400

    print(f"Received message: {data}")  # Prints to your VS Code terminal

    # Broadcast this message to all active browser dashboards
    for q in list(listeners):
        q.put(data)

    return {"status": "success"}, 200


@app.route("/stream")
def stream():
    # Server-Sent Events (SSE) generator for real-time browser updates
    def event_stream():
        q = queue.Queue()
        listeners.append(q)
        # Yield initial SSE comment immediately so response headers are sent to the browser right away
        yield ": connected\n\n"
        try:
            while True:
                try:
                    # Wait for message with a timeout for keep-alive pings
                    data = q.get(timeout=15)
                    yield f"data: {json.dumps(data)}\n\n"
                except queue.Empty:
                    # Send periodic keep-alive comment to keep connection alive
                    yield ": keep-alive\n\n"
        finally:
            if q in listeners:
                listeners.remove(q)

    response = app.response_class(event_stream(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
