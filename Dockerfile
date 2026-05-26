FROM python:3.10-bookworm
RUN apt-get update \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /abk
COPY ./abk/requirements.txt /abk/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
# to improve build times
COPY ./abk /abk
EXPOSE 5000
CMD ["python", "start.py"]