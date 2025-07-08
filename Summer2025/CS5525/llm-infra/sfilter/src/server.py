from flask import Flask, request, render_template_string
import os
import requests

from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import torch

app = Flask(__name__)

SECONDARY_MODEL = os.getenv("SECONDARY_MODEL")
if not SECONDARY_MODEL:
  raise ValueError("SECONDARY_MODEL environment variable is not set.")


#Log secondary model
app.logger.info(f"SECONDARY_MODEL = {SECONDARY_MODEL}")

try:
  tokenizer = AutoTokenizer.from_pretrained(SECONDARY_MODEL)
  model = AutoModelForSequenceClassification.from_pretrained(SECONDARY_MODEL)

  classifier = pipeline(
    "text-classification",
    model=model,
    tokenizer=tokenizer,
    truncation=True,
    max_length=8192,
    device=torch.device("cuda" if torch.cuda.is_available() else "cpu"),
  )
except Exception as e:
  app.logger.error(f"Error during startup: {e}")
  raise Exception(f"Error during startup: {e}, Secondary Model: {SECONDARY_MODEL}")



@app.route("/", methods=["POST"])
def main():
    userMessage = request.form.get('message', '')

    classification = classifier(userMessage)

    if classification[0]['label'] == 'jailbreak':
        #Missed jailbreak - passto DB (TODO)
        return "I don't understand your message, can you say it another way? (secondary)", 401

    return "ok", 200
            
if __name__ == "__main__":
    app.run(debug=True, port=8082, host='0.0.0.0')