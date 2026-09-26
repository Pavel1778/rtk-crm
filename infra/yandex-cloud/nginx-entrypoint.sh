#!/bin/sh
# Выбирает конфиг nginx по TLS_ENABLED и подставляет домен.
#
# Монтируется в контейнер nginx; шаблоны лежат рядом в /etc/nginx/templates.
# envsubst вызывается с явным списком переменных: если дать ему полный
# набор, он вырежет из конфига переменные самого nginx ($host, $uri, $scheme)
# и конфиг станет невалидным.
set -eu

DOMAIN="${DOMAIN:-localhost}"
TLS_ENABLED="${TLS_ENABLED:-false}"

case "$TLS_ENABLED" in
  true|1|yes|on)
    TEMPLATE=/etc/nginx/templates/nginx-tls.conf.template
    ;;
  *)
    TEMPLATE=/etc/nginx/templates/nginx-http.conf.template
    ;;
esac

echo "==> nginx: TLS_ENABLED=$TLS_ENABLED, домен=$DOMAIN, шаблон=$(basename "$TEMPLATE")"

envsubst '${DOMAIN}' < "$TEMPLATE" > /etc/nginx/conf.d/default.conf

exec nginx -g 'daemon off;'
