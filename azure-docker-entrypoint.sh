#!/bin/bash
set -e

# Enable SSH and give it access to app setting env variables
if [[ "$ENABLE_SSH" = "true" ]]; then
    service ssh start
    eval $(printenv | sed -n "/^PWD=/!s/^\([^=]\+\)=\(.*\)$/export \1=\2/p" | sed 's/"/\\\"/g' | sed '/=/s//="/' | sed 's/$/"/' >> /etc/profile)
fi

su -s /bin/bash bew --command "exec uwsgi --plugin http,python3 --master --http :8000 \
            --processes 4 --enable-threads \
            --static-map ${STATIC_URL}=${STATIC_ROOT} \
            --static-map /=${STATIC_ROOT} \
            --static-map /dashboard=/fileshare/dashboard \
            --static-map /docs=/fileshare/docs/api \
            --static-index index.html \
            --static-index index.htm \
            --need-app \
            --mount ${URL_PREFIX:-/}=parkkihubi/wsgi.py \
            --manage-script-name \
            --die-on-term \
            --strict"