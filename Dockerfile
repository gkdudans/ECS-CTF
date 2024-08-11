FROM python:3.10

WORKDIR /app
COPY . /app

RUN apt-get update && apt-get install -y \
    sudo \
    socat \
    iputils-ping \
    wget \
    unzip \
    gnupg 
    
#크롬설치
RUN apt -f install -y
RUN apt-get install -y wget
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN apt-get install ./google-chrome-stable_current_amd64.deb -y

#크롬드라이버
RUN wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/121.0.6167.85/linux64/chromedriver-linux64.zip \
     && unzip chromedriver-linux64.zip \
     && rm chromedriver-linux64.zip

EXPOSE 8080

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "app.py"]
