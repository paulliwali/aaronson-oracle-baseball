# Use python 3.11
FROM python:3.11-slim

# Set working directory in the container
WORKDIR /app 

# Copy requirements.txt and install dependcies
COPY requirements.txt requirements.txt 
RUN pip install -r requirements.txt 

# Copy the rest of the application code 
COPY . . 

# Expose port 5001 for flask 
EXPOSE 5001 

# Command to run the flask app 
CMD ["python", "main.py"]
