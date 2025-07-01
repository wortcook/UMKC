import os

import joblib
import logging
import json
import base64
import datetime
import hashlib

from flask import Flask

app = Flask(__name__)
clf = joblib.load("model.pkl")
cv = joblib.load("cv.pkl")
deployHash = joblib.load("deployHash.txt")

def process_text(text: str) -> str:
    #Break into words
    words = text.split(" ")
    for word in words:
        #Remove words that are less than 3 characters
        if len(word) == 1:
            words.remove(word)
        else:
            #Remove all vowels
            word = word.replace("aeiou", "")
            #Remove all numbers
            word = word.replace("0123456789", "")
        
    #Rejoin the words
    text = " ".join(words)
    #Save the text
    return text

@app.route("/", methods=["POST"])
def main():
    userMessage = request.form.get('message')
    #truncate the message to 3000 characters
    userMessage = userMessage[:3000].lower()

    # default score is 1        
    score = 1
        
    userMessage = process_text(userMessage)
        
    # if the message is not empty, score it
    # otherwise the score is always 1
    if len(userMessage) > 0:
        v = cv.transform([userMessage]).toarray()

        # score the message as the probability of a positive (spam) message
        score =clf.predict_proba(v)[0][1]
    else:
        score = 1
    
    if score > 0.9: #treat as spam
        return "I don't understand your message, can you say it another way?"
    elif score > 0.3: #treat as neutral
        return "Placeholder call secondary"
    else:
        return "Placeholder call LLM"

if __name__ == "__main__":
    app.run(debug=True, port=8082, host='0.0.0.0')