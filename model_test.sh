#!/bin/bash
# Bir modelin gercekten cevap verip vermedigini olcer.
# Bu projeden bagimsiz: yalnizca NVIDIA'ya duz bir HTTP istegi atar.
#
#   wsl -e bash /root/projects/oc-mcp/model_test.sh
#
# Bir model adi verilirse yalnizca onu dener.

set -a
. /root/projects/oc-mcp/.env 2>/dev/null
set +a

if [ -z "$NVIDIA_API_KEY" ]; then
    echo "NVIDIA_API_KEY bulunamadi (.env okunamadi)"
    exit 1
fi

ADRES="https://integrate.api.nvidia.com/v1/chat/completions"

if [ -n "$1" ]; then
    MODELLER="$1"
else
    MODELLER="nvidia/nemotron-3-ultra-550b-a55b
nvidia/nemotron-3-super-120b-a12b
nvidia/nemotron-3.5-lightning-30b-a3b
openai/gpt-oss-120b"
fi

printf '%-42s %-9s %-8s %s\n' MODEL HTTP SURE CEVAP
printf '%.0s-' {1..90}; echo

echo "$MODELLER" | while read -r M; do
    [ -z "$M" ] && continue
    GOVDE=$(printf '{"model":"%s","messages":[{"role":"user","content":"merhaba"}],"max_tokens":20}' "$M")
    OLCU=$(curl -s -m 60 -o /tmp/model_cevap.txt \
                -w '%{http_code} %{time_total}' \
                "$ADRES" \
                -H "Authorization: Bearer $NVIDIA_API_KEY" \
                -H "Content-Type: application/json" \
                -d "$GOVDE")
    KOD=$(echo "$OLCU" | cut -d' ' -f1)
    SURE=$(echo "$OLCU" | cut -d' ' -f2)
    METIN=$(head -c 400 /tmp/model_cevap.txt \
            | tr -d '\n' \
            | sed -e 's/.*"content":"//' -e 's/".*//' \
            | cut -c1-34)
    [ "$KOD" = "000" ] && METIN="(zaman asimi -- cevap yok)"
    [ "$KOD" = "404" ] && METIN="(NVIDIA servis vermiyor)"
    printf '%-42s %-9s %-8s %s\n' "$M" "$KOD" "${SURE}s" "$METIN"
done

echo
echo "HTTP 200 = calisiyor   404 = servis yok   000 = asili kaldi"
