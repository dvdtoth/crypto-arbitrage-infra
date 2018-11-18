yum install squid haproxy -y
systemctl enable squid
systemctl enable haproxy
service squid start
service haproxy start