FROM python:3.11

# Copy function code
COPY src/server.py .
COPY src/dataprep.py .

# Copy requirements.txt
COPY src/requirements.txt .

# Copy the CSV training data
COPY data/jailbreaks.csv .

# Install the specified packages
RUN pip install -r requirements.txt

# Run the data prep script to create the pickles
RUN python ./dataprep.py

# Remove the files that are no longer needed
RUN rm ./dataprep.py
RUN rm ./jailbreaks.csv
RUN rm ./requirements.txt

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD ["gunicorn", "-b", "0.0.0.0:8082", "server:app"]

