FROM python:3.7-alpine

EXPOSE 5000

COPY ./ytarchive /ytarchive

WORKDIR /ytarchive

ENV PYTHONPATH="$PYTHONPATH:/ytarchive" 

RUN apk update
RUN apk add alpine-sdk mariadb-connector-c mariadb-connector-c-dev
RUN apk add --no-cache bash
RUN apk add youtube-dl

RUN pip install internetarchive
RUN pip install -r requirements.txt
RUN mv ia.ini ~/.ia

CMD python app.py
