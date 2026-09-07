#!/bin/bash
# Makale "yeniden uretilebilirlik" bolumu icin ortam bilgisi.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "--- isletim sistemi ---"
grep PRETTY_NAME /etc/os-release | cut -d= -f2- | tr -d '"'
echo "--- cekirdek ---"
uname -r
echo "--- derleyiciler ---"
gfortran --version | head -1
gcc --version | head -1
echo "--- OpenCalphad kutuphaneleri ---"
# Motorun yeri sunucunun kendi cozumlemesinden; burada ikinci bir yol
# yazmak onu eskimeye birakmak olurdu.
BUILD="${OC_BUILD_DIR:-$(cd "$HERE" && python3 -c \
    'import paths; print(paths.build_dir())' 2>/dev/null)}"
for f in "$BUILD/.libs/libOPENCALPHAD.so.0" \
         "$BUILD/.libs/libOC.so.0" \
         "$BUILD/OC"; do
    [ -e "$f" ] && stat -c '%n  %s bayt  %y' "$f" | cut -d. -f1
done
echo "--- yerel ikili (6.058) ---"
W='/mnt/c/OpenCalphad_CAE_0_1_0/Console/Windows/oc6P.exe'
[ -f "$W" ] && stat -c '%n  %s bayt  %y' "$W" | cut -d. -f1 || echo "bulunamadi"
echo "--- TDB veritabani sayisi ---"
# Klasoru sunucunun kendi cozumlemesinden sor; burada ikinci bir
# yol yazmak onu eskimeye birakmak olurdu.
DB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && OC_QUIET=1 python3 -c "import oc_service; print(oc_service.DEFAULT_DB_DIR)" 2>/dev/null)"
ls "${DB_DIR:-.}"/*.TDB 2>/dev/null | wc -l
