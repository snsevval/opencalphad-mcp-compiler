"""parse_verdict'in son isareti aldigini dogrular.

Canli vakadan: deepseek "SONUC: BASARISIZ" ile acti, gerekcesini yazdi,
"basarili kabul edilmelidir" ile kapatti. Eski ayristirici ILK isareti
aldigi icin dogru bir hesabi hatali isaretledi.
"""
import sys

sys.path.insert(0, "/root/projects/oc-mcp")
import semantic_check as sc  # noqa: E402

CANLI_VAKA = (
    "SONUC: BASARISIZ\n\n"
    "Gerekçe: ... fiziksel olarak tutarlıdır ... toplam karbon korunumu "
    "kontrol edildiğinde 0.01, bu doğrudur ... herhangi bir hata veya NaN "
    "bulunmamaktadır. Sonuç fiziksel olarak tutarlıdır ve başarılı kabul "
    "edilmelidir.\n"
)

CASES = [
    ("son isaret BASARILI (yeni bicim)",
     "Gerekçe: faz toplamı 1.0, geçişler makul.\nSONUC: BASARILI", True),
    ("son isaret BASARISIZ (yeni bicim)",
     "Gerekçe: 800 K'de sıvı görünüyor, imkânsız.\nSONUC: BASARISIZ", False),
    ("tek isaret basta (eski bicim, hala calismali)",
     "SONUC: BASARILI\nGerekçe: her şey yerinde.", True),
    ("celiskili: basta BASARISIZ, sonda BASARILI",
     "SONUC: BASARISIZ\nGerekçe: ...\nSONUC: BASARILI", True),
    ("isaret yok, sadece olumlu kelimeler",
     "Sonuç tutarlı ve makul görünüyor.", True),
    ("isaret yok, sadece olumsuz kelimeler",
     "Sonuç tutarsız, fiziksel olarak yanlış.", False),
    ("belirsiz -> None",
     "Bir kısmı tutarlı ama bir kısmı yanlış görünüyor.", None),
]

ok = 0
for ad, metin, beklenen in CASES:
    got = sc.parse_verdict(metin)
    gecti = (got is beklenen) if beklenen is None else (got == beklenen)
    print(f"[{'GECTI' if gecti else 'BASARISIZ'}] {ad}: beklenen={beklenen} alinan={got}")
    ok += 1 if gecti else 0

print()
print("--- CANLI VAKA (regresyon) ---")
# Tek isaret var (BASARISIZ) ama kapanis cumlesi tersini soyluyor.
# Dogru davranis: karari CEVIRMEK degil, "okunamadi" (None) demek --
# hangi yarisini kastettigini bilmiyoruz, tahmin etmek yasak.
got = sc.parse_verdict(CANLI_VAKA)
gecti = (got is None)
print(f"[{'GECTI' if gecti else 'BASARISIZ'}] eski ayristirici False verirdi; yeni: {got} (beklenen None)")
ok += 1 if gecti else 0

print()
print("--- CELISKI YOKKEN BOZULMAMALI ---")
EK = [
    ("normal BASARISIZ + olumsuz gerekce",
     "SONUC: BASARISIZ\nGerekçe: 800 K'de sıvı var, bu tutarsız.", False),
    ("normal BASARILI + olumlu gerekce",
     "SONUC: BASARILI\nGerekçe: faz geçişleri makul, değerler doğru.", True),
]
for ad, metin, beklenen in EK:
    g = sc.parse_verdict(metin)
    gg = (g == beklenen)
    print(f"[{'GECTI' if gg else 'BASARISIZ'}] {ad}: beklenen={beklenen} alinan={g}")
    ok += 1 if gg else 0

toplam = len(CASES) + 1 + len(EK)
print()
print(f"SONUC: {ok}/{toplam}")
sys.exit(0 if ok == toplam else 1)
