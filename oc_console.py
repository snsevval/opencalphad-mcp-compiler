# -*- coding: utf-8 -*-
"""Motoru SORDUGU seye gore surer, kac soru soracagini sayarak degil.

Bu modul bir mimari borcu kapatiyor. Motor bir konsol programi ve simdiye
kadar ona bir makro DOSYASI stdin'den veriliyordu: satirlar sirayla
okunuyor, ve her satir o an hangi istem geldiyse ona cevap oluyor. Yani
makro "motor su noktada tam su kadar soru soracak" varsayimini tasiyordu,
ve varsayim yazili degildi -- bos satir sayilarinda gomuluydu.

Varsayim tutmadiginda ne oldugu olculdu ve kodda yazili: iron4cd yuklenirken
uyari verip RETURN bekliyor, bir sonraki makro satiri o istemi cevapliyor,
`set condition` hic ulasmiyor, ve hesap KOSULSUZ kosup G=0 ile NaN
donduruyor. Disaridan bakan icin bu, cozulemeyen bir alasim gibi gorunuyor.
Duzeltme o gun dort bos satir eklemek oldu -- tamponu buyutmek, varsayimi
kaldirmak degil.

ON KOSUL OLCULDU. Uc sey de dogru cikti:
  1  Motor istemi, cevabi beklemeden ONCE yaziyor. Bos bir boruyla
     baslatilip uc saniye beklendiginde stdout "--->OC6:" ile bitiyor.
  2  Istemler ayirt edilebiliyor: "--->OC6:" komut istemi, digerleri
     sordugu seyi yaziyor ("Select elements", "Step options?",
     "LIST what?", "Dependent values").
  3  Varsayilan istemin ICINDE yazili: /all/, /NORMAL/, /RESULTS/,
     /NP(*)/. Yani "varsayilani kabul et" diye bir cevap her zaman var
     ve bos satirla veriliyor.

UCUNCU BIR ISTEM BICIMI VAR ve hicbir noktalama tasimiyor. Bir uyari
verdikten sonra motor su iki satiri basip bekliyor:

    There were warnings, check them carefully
    and press RETURN if you wish to continue.

Ne "--->OC6:" var ne "/varsayilan/:". Konumsal makronun "bir degil DORT
bos satir" yamasi tam bunu tamponluyordu -- ve tamponladigi seyin ne
oldugu yazili degildi, cunku disaridan gorulebilen tek sey satir sayisiydi.
Burada adi var: bir RETURN istemi, cevabi bos satir, ve bir adimi
harcamiyor.

ISTEMLER AYNI SATIRDA BIRIKIYOR. Motor istemden sonra satir sonu koymuyor,
o yuzden ardisik istemler "--->OC6:--->OC6:" diye birlesiyor. Sondaki
satira bakmak bu yuzden yanlis cevap verir; istemler SAYILIYOR, ve kacina
cevap verildigi tutuluyor.
"""
import os
import re
import subprocess
import time


# Iki farkli "istem gelmedi". Ayri nesneler, cunku ayri kararlar
# veriyorlar ve None ikisini de temsil edemez.
_CIKTI = object()      # surec gitti: kosum bitti, basarisiz bitmis olsa da
_SESSIZ = object()     # surec yasiyor ama susuyor: takilma


class ConsoleError(Exception):
    """Motor beklenen istemi hic sormadi, ya da hic konusmayi birakti.

    `stalled` ikisini ayiriyor ve ayrim pahali: YASAYAN bir surecin
    susmasi takilmadir ve tekrar denemeye deger; CIKMIS bir surec zaten
    bitmistir, basarisiz bitmis olsa bile, ve tekrar denemek ayni cevap
    icin zamani iki kez harcar. Olculdu -- alni-4slx'te 0,3 saniyede biten
    deterministik bir hata, ayrim yokken 60,8 saniye surdu.
    """

    def __init__(self, message, stalled=False):
        super().__init__(message)
        self.stalled = stalled


# Komut istemi, ya da varsayilanini /.../ icinde tasiyan bir parametre
# istemi. Ikinci desen kasitli olarak dar: /.../ arasinda satir sonu ya da
# baska bir bolu isareti olamaz, cunku motorun bastigi metin icinde
# "kg/m3" gibi seyler geciyor ve onlar istem degil.
PROMPT = re.compile(
    r"--->OC6:"                       # komut istemi
    r"|/[^/\n]{0,60}/:"               # parametre istemi, varsayilani icinde
    r"|press RETURN[^\n]*"            # noktalama tasimayan ucuncu bicim
)


def _prompt_text(metin, m):
    """Bir istem belirteci ve onunden gelen soru metni.

    Ayni satirda birden fazla istem olabildigi icin, bu istemin metni bir
    onceki istemin bittigi yerden basliyor -- satirin bası degil.
    """
    satir_bas = metin.rfind("\n", 0, m.start()) + 1
    onceki = metin.rfind("OC6:", satir_bas, m.start())
    bas = satir_bas if onceki < 0 else onceki + len("OC6:")
    return metin[bas:m.end()].strip()


def run_script(binary, cwd, steps, env=None, timeout=180.0, silence=30.0,
               stdout_path=None, stop_when=None, settle=1.0, on_stall=None):
    """Motoru surer ve stdout metnini dondurur.

    steps: (beklenen, gonderilecek) ciftlerinin listesi. `beklenen` istem
    metninde aranan bir alt dizge (buyuk/kucuk harf onemsiz), ya da None --
    None "sirada ne gelirse" demektir ve yalnizca gercekten fark etmedigi
    yerde kullanilmali.

    Beklenen istem yerine baska bir istem gelirse BOS SATIR gonderiliyor:
    varsayilani kabul et, ve komutu HARCAMA. Konumsal makronun yapamadigi
    tam olarak buydu -- orada beklenmedik bir istem bir sonraki komutu
    yiyordu. Kac kez oldugu dondurulyor, cunku "hicbir sey olmadi" ile
    "iki surpriz soruldu ve gecildi" ayri seyler ve ikincisi kayda deger.

    stop_when(metin) verilirse, adimlar bittikten sonra o dogru olana
    kadar beklenir; motorun cikmasini beklemekten daha kesin bir bitis.

    Sessizlik kurali korunuyor: takilan bir kosum uretmeyi birakir, yavas
    olan birakmaz, ve ikisini ayiran sey saat degil sessizliktir.
    """
    stdout_path = stdout_path or os.path.join(cwd, "oc_stdout.txt")
    cevaplanan = 0
    beklenmeyen = []
    basladi = time.monotonic()
    deadline = basladi + timeout

    with open(stdout_path, "w") as f_out:
        proc = subprocess.Popen(
            [binary], cwd=cwd,
            stdin=subprocess.PIPE, stdout=f_out, stderr=subprocess.STDOUT,
            env=env, text=True, bufsize=1)

        def oku():
            try:
                with open(stdout_path, errors="ignore") as f:
                    return f.read()
            except OSError:
                return ""

        def sonraki_istem():
            """Cevaplanmamis ilk istem, ya da None (sessizlik/zaman asimi)."""
            son_boyut, son_degisim = -1, time.monotonic()
            while time.monotonic() < deadline:
                metin = oku()
                hepsi = list(PROMPT.finditer(metin))
                if len(hepsi) > cevaplanan:
                    return _prompt_text(metin, hepsi[cevaplanan])
                if len(metin) != son_boyut:
                    son_boyut = len(metin)
                    son_degisim = time.monotonic()
                elif time.monotonic() - son_degisim > silence:
                    return _SESSIZ
                if proc.poll() is not None:
                    return _CIKTI
                time.sleep(0.05)
            return _SESSIZ            # deadline: konusmayi birakmis sayilir

        def yaz(satir):
            try:
                proc.stdin.write(satir + "\n")
                proc.stdin.flush()
            except (BrokenPipeError, ValueError):
                raise ConsoleError(
                    "the engine closed its input before the script finished")

        try:
            for beklenen, gonderilecek in steps:
                # En fazla sekiz surpriz istem. Sinir keyfi degil: her biri
                # bir bos satir maliyeti, ve sekizden fazlasi artik
                # "beklenmedik bir soru" degil, "yanlis yerdeyiz" demektir.
                for _ in range(8):
                    istem = sonraki_istem()
                    if istem is _CIKTI or istem is _SESSIZ:
                        # The caller gets one look at the live process
                        # before it is killed. Without this the only
                        # diagnostic left is the text, and a stall that
                        # produces no text is exactly the case that needs
                        # one.
                        rapor = ""
                        if on_stall is not None and istem is _SESSIZ:
                            try:
                                rapor = on_stall(proc, oku()) or ""
                            except Exception:            # noqa: BLE001
                                rapor = ""
                        raise ConsoleError(
                            "engine %s while waiting for %r (answered %d "
                            "prompts, %d of them unexpected)%s"
                            % ("exited" if istem is _CIKTI
                               else "stopped prompting",
                               beklenen, cevaplanan, len(beklenmeyen),
                               (" [%s]" % rapor) if rapor else ""),
                            stalled=(istem is _SESSIZ))
                    if beklenen is None or beklenen.lower() in istem.lower():
                        break
                    beklenmeyen.append(istem)
                    yaz("")
                    cevaplanan += 1
                else:
                    raise ConsoleError(
                        "the engine never asked for %r; it asked %s"
                        % (beklenen, beklenmeyen[-3:]))
                yaz(gonderilecek)
                cevaplanan += 1

            # Adimlar bitti. Motorun son ciktisini yazmasi icin kisa bir
            # sure taniniyor; kapatma onu kesebilir.
            if stop_when is not None:
                son = time.monotonic() + min(silence, max(0.0, deadline - time.monotonic()))
                while time.monotonic() < son:
                    if stop_when(oku()):
                        break
                    time.sleep(0.05)
            else:
                time.sleep(settle)
        finally:
            try:
                proc.stdin.close()
            except Exception:                            # noqa: BLE001
                pass
            proc.kill()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass

    return oku(), beklenmeyen
