#!/bin/bash
# Script para verificar TODOS los timeouts en el sistema

echo "==================================================================="
echo "Verificación Completa de Timeouts - Whisper ASR"
echo "==================================================================="
echo ""

echo "1️⃣  Verificando Nginx..."
echo "-------------------------------------------------------------------"
if command -v nginx &> /dev/null; then
    echo "client_max_body_size:"
    nginx -T 2>/dev/null | grep -i "client_max_body_size" | head -5
    echo ""
    echo "Timeouts:"
    nginx -T 2>/dev/null | grep -E "(client_body_timeout|client_header_timeout|send_timeout|proxy.*timeout|keepalive_timeout)" | head -15
    echo ""
else
    echo "Nginx no encontrado"
fi

echo ""
echo "2️⃣  Verificando Apache..."
echo "-------------------------------------------------------------------"
if command -v apache2ctl &> /dev/null; then
    echo "Timeout general:"
    apache2ctl -t -D DUMP_RUN_CFG 2>/dev/null | grep -i timeout || grep -r "^Timeout" /etc/apache2/ 2>/dev/null | head -3
    echo ""
    echo "ProxyTimeout:"
    grep -r "ProxyTimeout" /etc/apache2/ 2>/dev/null | head -3
    echo ""
    echo "LimitRequestBody:"
    grep -r "LimitRequestBody" /etc/apache2/ 2>/dev/null | head -3
    echo ""
elif command -v httpd &> /dev/null; then
    echo "Apache httpd detectado"
    httpd -t -D DUMP_RUN_CFG 2>/dev/null | grep -i timeout
else
    echo "Apache no encontrado"
fi

echo ""
echo "3️⃣  Verificando configuración de Plesk para whisper.suils.es..."
echo "-------------------------------------------------------------------"
DOMAIN_CONF=$(find /var/www/vhosts/suils.es -name "vhost*.conf" 2>/dev/null)
if [ -n "$DOMAIN_CONF" ]; then
    echo "Archivos de configuración encontrados:"
    echo "$DOMAIN_CONF"
    echo ""
    for conf in $DOMAIN_CONF; do
        echo "Contenido de $conf:"
        grep -E "(Timeout|LimitRequestBody|client_max_body_size|proxy.*timeout)" "$conf" 2>/dev/null || echo "  No se encontraron directivas de timeout"
        echo ""
    done
else
    echo "No se encontraron archivos de configuración del dominio"
fi

echo ""
echo "4️⃣  Verificando Docker Container..."
echo "-------------------------------------------------------------------"
if command -v docker &> /dev/null; then
    echo "Estado del contenedor:"
    docker ps | grep whisper || echo "Contenedor no encontrado"
    echo ""
    echo "Variables de entorno:"
    docker compose exec -T whisper-asr-webservice env 2>/dev/null | grep -E "(ASR_|MAX_|TIMEOUT)" || echo "No se pudo obtener variables"
    echo ""
else
    echo "Docker no encontrado"
fi

echo ""
echo "5️⃣  Verificando límites del sistema..."
echo "-------------------------------------------------------------------"
echo "Ulimit (límites de archivos y procesos):"
ulimit -a | grep -E "(file|time|memory)"
echo ""

echo ""
echo "==================================================================="
echo "🔍 DIAGNÓSTICO"
echo "==================================================================="
echo ""
echo "Si ves timeouts menores a 7200s en cualquier parte, ese es el problema."
echo ""
echo "Soluciones comunes:"
echo "1. Nginx: Editar el vhost de Plesk y agregar timeouts largos"
echo "2. Apache: Agregar 'Timeout 7200' y 'ProxyTimeout 7200'"
echo "3. Plesk: Usar el panel web para configurar directivas adicionales"
echo ""
echo "Archivos importantes:"
echo "- Nginx: /etc/nginx/plesk.conf.d/vhosts/suils.es_nginx.conf"
echo "- Apache: /etc/apache2/plesk.conf.d/vhosts/suils.es_apache.conf"
echo "- Plesk: Panel web > Dominios > whisper.suils.es > Apache & nginx"
echo ""
