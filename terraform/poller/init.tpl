#!/bin/bash

yum install docker git -y
curl -L "https://github.com/docker/compose/releases/download/1.23.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
usermod -a -G docker ec2-user
systemctl enable docker
service docker start
git clone https://github.com/wurstmeister/kafka-docker.git
cat > 
docker-compose -f kafka-docker/kafka-single.yml up -d
git clone https://oauth2:${gitlab_token}@gitlab.com/cryptoindex/orderbook-poller.git
docker-compose -f orderbook-poller/docker-compose.yml up -d


sudo su
yum install git -y
amazon-linux-extras install docker -y
usermod -a -G docker ec2-user
systemctl enable docker
service docker start