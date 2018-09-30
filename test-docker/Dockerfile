FROM postgres:alpine
COPY create-user.sh /docker-entrypoint-initdb.d/create-user.sh
RUN chmod +x /docker-entrypoint-initdb.d/create-user.sh

CMD ["postgres"]
