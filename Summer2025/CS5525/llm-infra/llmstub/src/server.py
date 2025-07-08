import os
from flask import Flask
from flask import request


app = Flask(__name__)

@app.route("/", methods=["POST"])
def main():
    return request.form.get('message')

if __name__ == "__main__":
    app.run(debug=True, port=8081, host='0.0.0.0')