#!/bin/bash
# Makale "yeniden uretilebilirlik" bolumu icin ortam bilgisi.
echo "--- isletim sistemi ---"
grep PRETTY_NAME /etc/os-release | cut -d= -f2- | tr -d '"'
echo "--- cekirdek ---"
uname -r
echo "--- derleyiciler ---"
gfortran --version | head -1
gcc --version | head -1
echo "--- OpenCalphad kutuphaneleri ---"
for f in /root/projects/opencalphad/.libs/libOPENCALPHAD.so.0 \
         /root/projects/opencalphad/.libs/libOC.so.0 \
         /root/projects/opencalphad/OC; do
    [ -e "$f" ] && stat -c '%n  %s bayt  %y' "$f" | cut -d. -f1
done
echo "--- yerel ikili (6.058) ---"
W='/mnt/c/OpenCalphad_CAE_0_1_0/Console/Windows/oc6P.exe'
[ -f "$W" ] && stat -c '%n  %s bayt  %y' "$W" | cut -d. -f1 || echo "bulunamadi"
echo "--- TDB veritabani sayisi ---"
ls /mnt/c/Users/sevval/Documents/OpenCalphad/OC6/macros/*.TDB 2>/dev/null | wc -l
