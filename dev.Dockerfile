# pawanprjl/python-nginx:alpine is merge of official python and nginx images.
FROM pawanprjl/python-nginx

ENV PIP_ROOT_USER_ACTION ignore
ENV PIP_DISABLE_PIP_VERSION_CHECK 1

HEALTHCHECK --interval=10s --timeout=2s --start-period=10s --retries=3 CMD pgrep nginx && pgrep python3 >> /dev/null || exit 1

VOLUME  ["/etc/nginx/dhparam", "/tmp/acme-challenges/","/etc/nginx/conf.d"]

WORKDIR /app

# copy project
COPY . .

# install required packages
RUN apk --no-cache add openssl \
    && apk add --no-cache --virtual .build-deps \
    gcc libc-dev openssl-dev linux-headers libffi-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -f requirements.txt && apk del .build-deps

# symlink docker-entrypoint.sh at root path
RUN ln -s /app/docker-entrypoint.sh /docker-entrypoint.sh

ARG LETSENCRYPT_API="https://acme-staging-v02.api.letsencrypt.org/directory"

ENV LETSENCRYPT_API=${LETSENCRYPT_API}

CMD ["sh", "-e", "/docker-entrypoint.sh"]
