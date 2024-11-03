FROM python:3.9

WORKDIR /app

COPY . /app

# Create a virtual environment in the container
RUN python -m venv venv

# Activate the virtual environment and install dependencies
# Use the path to the venv directly for commands
RUN . venv/bin/activate && pip install -r requirements.txt

# Update the CMD to use the virtual environment
CMD ["venv/bin/python", "app.py"]
