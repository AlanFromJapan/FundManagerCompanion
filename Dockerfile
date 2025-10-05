FROM python:3.12-alpine

WORKDIR /app

COPY . /app

# Install Python dependencies if requirements.txt exists
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

EXPOSE 5000

#Create a user to run the application NOT as root
RUN adduser --disabled-password --gecos '' --no-create-home  webuser
USER webuser

#Run the application (-u is to avoid buffering)
CMD ["python3", "-u", "app.py"]
