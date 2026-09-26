FROM python:3.12-alpine

WORKDIR /app

# Install build dependencies for Python packages (scikit-learn)
RUN apk update && apk add python3-dev gcc libc-dev g++

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies if requirements.txt exists
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Copy application code
COPY . .

EXPOSE 5000

#Create a user to run the application NOT as root
RUN adduser --disabled-password --gecos '' --no-create-home  webuser
USER webuser

#Run the application (-u is to avoid buffering)
CMD ["python3", "-u", "app.py"]
