Nginx-Proxy
===================================================
Docker container for automatically creating nginx configuration based on active containers in docker host.

- Easy server configuration with environment variables
- Map multiple containers to different locations on same server
- Automatic Let's Encrypt ssl certificate registration


## Quick Setup
### Setup nginx-proxy
```
docker pull pawanprjl/nginx-proxy
docker network create frontend;    # create a network for nginx proxy
docker run  --network frontend \
            --name nginx-proxy \
            -v /var/run/docker.sock:/var/run/docker.sock:ro \
            -v /etc/nginx/conf.d:/etc/nginx/conf.d \
            -v /etc/nginx/dhparam:/etc/nginx/dhparam \
            -p 80:80 \
            -p 443:443 \
            -d --restart always pawanprjl/nginx-proxy
```

### Setup your container
The only thing that matters is that the container shares at least one common network to the nginx container and `VIRTUAL_HOST` environment variable is set.

Examples:
- **WordPress**
```
docker run --network frontend \
          --name wordpress-server \
          -e VIRTUAL_HOST="wordpress.example.com" \
          wordpress
```
