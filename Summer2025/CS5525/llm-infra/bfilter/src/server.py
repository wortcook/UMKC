import json

import joblib
from flask import Flask, request, render_template_string
import os
import requests
from google.auth.transport import requests as auth_requests
from google.oauth2 import id_token as google_id_token
from google.cloud import pubsub_v1

LLMSTUB_URL = os.getenv("LLMSTUB_URL")
SFILTER_URL = os.getenv("SFILTER_URL")

#MODEL LOAD FOR BAYESIAN FILTER
clf = joblib.load("model.pkl")
cv = joblib.load("cv.pkl")

app = Flask(__name__)

# The deployHash is loaded but not used in this file.
# It can be uncommented if needed for logging or headers.
# deployHash = joblib.load("deployHash.txt")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Message Filter</title>
    <style>
        body { font-family: sans-serif; margin: 2em; background-color: #f4f4f9; color: #333; }
        h1, h2 { color: #444; }
        form { background: white; padding: 2em; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        textarea { width: 100%; min-height: 100px; margin-bottom: 1em; border: 1px solid #ccc; border-radius: 4px; padding: 0.5em; box-sizing: border-box; }
        input[type="submit"] { background-color: #007bff; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 1em; }
        input[type="submit"]:hover { background-color: #0056b3; }
        #response { background-color: #e9ecef; }
    </style>
</head>
<body>
    <h1>Enter a message to classify</h1>
    <form id="messageForm">
        <label for="message">Message:</label><br>
        <textarea id="message" name="message" rows="5" cols="50" required></textarea><br>
        <input type="submit" value="Submit">
    </form>

    <h2>Response:</h2>
    <textarea id="response" name="response" rows="5" cols="50" readonly></textarea>

    <script>
        document.getElementById('messageForm').addEventListener('submit', function(event) {
            event.preventDefault(); // Prevent the default form submission

            const message = document.getElementById('message').value;
            const responseArea = document.getElementById('response');

            responseArea.value = 'Processing...'; // Show a processing message

            fetch('/handle', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: 'message=' + encodeURIComponent(message)
            })
            .then(response => response.text())
            .then(data => {
                responseArea.value = data;
            })
            .catch(error => {
                console.error('Error:', error);
                responseArea.value = 'Error processing your request.';
            });
        });
    </script>
</body>
</html>
"""

def process_text(text: str) -> str:
    """
    Creates a new version of text processing, per the request.
    This version filters out short words and corrects the iteration bug
    from the original script. It does not include the text reversal logic.
    """
    words = text.split(" ")
    processed_words = [word for word in words if len(word) > 1]
    return " ".join(processed_words)

def make_authenticated_post_request(url: str, data: dict) -> requests.Response:
    """
    Makes an authenticated POST request to a Google Cloud Run service.

    This function fetches a Google-signed ID token for the target audience (URL)
    and includes it in the Authorization header of the POST request. It will
    raise an HTTPError for 4xx or 5xx responses.

    Args:
        url: The URL of the Cloud Run service to call.
        data: The dictionary of data to send in the POST request body.

    Returns:
        The requests.Response object from the call.
    """
    auth_req = auth_requests.Request()
    identity_token = google_id_token.fetch_id_token(auth_req, url)
    headers = {"Authorization": f"Bearer {identity_token}"}
    response = requests.post(url, data=data, headers=headers)
    response.raise_for_status()
    return response

@app.route("/")
def index():
    """Serves the HTML form."""
    return render_template_string(HTML_TEMPLATE)

@app.route("/handle", methods=["POST"])
def main():
    userMessage = request.form.get('message', '')
    testMessage = userMessage.lower().replace("aeiou0123456789", "")

    score = 0.0

    if userMessage.strip():
        processed_message = process_text(testMessage)
        if processed_message:
            v = cv.transform([processed_message]).toarray()
            score = clf.predict_proba(v)[0][1]

    if score < 0.9:
        # If the score is low, proceed to the secondary filter (sfilter).
        try:
            make_authenticated_post_request(SFILTER_URL, data={"message": userMessage})
        except requests.exceptions.HTTPError as e:
            # sfilter returns a 401 on jailbreak detection.
            if e.response.status_code == 401:

                #fire pub-sub event to "secondary-filter"
                try:
                    #Pub/Sub
                    # The ID of your Google Cloud project
                    project_id = os.getenv("PROJECT_ID")
                    # The ID of your Pub/Sub topic
                    topic_id = "secondary-filter"

                    publisher = pubsub_v1.PublisherClient()
                    # The `topic_path` method creates a fully qualified identifier
                    # in the form `projects/{project_id}/topics/{topic_id}`
                    topic_path = publisher.topic_path(project_id, topic_id)

                    # Data must be a byte string
                    data = json.dumps({"message": userMessage}).encode("utf-8")
                    # When you publish a message, the client returns a future.
                    future = publisher.publish(topic_path, data)
                    message_id = future.result()
                    app.logger.info(f"Published message to {topic_path}: {message_id}")
                except Exception as e:
                    app.logger.error("Error publishing event")
                    return f"Error publishing event {e}", 503


                app.logger.info("sfilter service detected a jailbreak.")
                return "I don't understand your message, can you say it another way? (secondary)"
            else:
                app.logger.error(f"HTTP error during sfilter check for URL {SFILTER_URL}: {e}")
                return f"Error communicating with the secondary filter. {response.status_code}", 503

        # If sfilter passes (returns 200 OK), call the final LLM stub.
        try:
            llmstub_response = make_authenticated_post_request(LLMSTUB_URL, data={"message": userMessage})
            return llmstub_response.text
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Error calling llmstub service at {LLMSTUB_URL}: {e}")
            return "Error communicating with the primary service.", 503
    else:
        return "I don't understand your message, can you say it another way?"

if __name__ == "__main__":
    app.run(debug=True, port=8082, host='0.0.0.0')