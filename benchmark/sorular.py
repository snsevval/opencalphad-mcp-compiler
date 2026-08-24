"""cases.py'den okunabilir bir soru listesi uretir (SORULAR.md).

Vaka kaydi tek dogru kaynak: soru metni, sinadigi sey ve beklenen cevap
oradan okunur, elle kopyalanmaz. Boylece liste ile kosucunun puanladigi
sey birbirinden ayrilamaz.

    python3 benchmark/sorular.py > benchmark/SORULAR.md
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import cases  # noqa: E402

GRUPLAR = [
    ("A", "Tek fazlı denge", "A_TEK_FAZ"),
    ("B", "Çok fazlı denge ve element paylaşımı", "B_COK_FAZ"),
    ("C", "Faz geçişleri (sıcaklık taraması)", "C_FAZ_GECISI"),
    ("D", "Bileşim kümeleri ve karışmazlık boşluğu", "D_BILESIM_KUMESI"),
    ("E", "Yarı kararlı hesap (faz kapatma)", "E_YARI_KARARLI"),
    ("F", "İki bileşimin karşılaştırılması", "F_KARSILASTIRMA"),
    ("G", "Çelik dışı sistemler (oksit, tuz, gaz)", "G_CELIK_DISI"),
    ("H", "Bileşim ekseni (izotermal kesit)", "H_BILESIM_EKSENI"),
    ("I", "Katılaşma (Scheil-Gulliver)", "I_KATILASMA"),
    ("J", "Faz diyagramı (iki eksen, MAP)", "J_FAZ_DIYAGRAMI"),
    ("R", "Doğru red — reddedilmesi gereken istekler", "DOGRU_RED"),
    ("S", "Doğru rapor — anlatının doğruluğu", "DOGRU_RAPOR"),
]

STOKIYOMETRI_ADI = {
    round(6 / 29, 6): "6/29",
    round(3 / 10, 6): "3/10",
    round(1 / 7, 6): "1/7",
    round(1 / 2, 6): "1/2",
}


def beklenen_metni(case):
    """Beklenen cevabi, hesap makinesiyle kontrol edilebilir maddelere
    cevirir. Hicbir madde uzmanlik gerektirmemeli."""
    e = case["expected"]
    satirlar = []

    if e.get("rejected"):
        satirlar.append("**Hesap yapılmamalı.** İstek reddedilmeli.")
        if e.get("stage") == "PREFLIGHT":
            satirlar.append("Red, motor çalışmadan önce (PREFLIGHT) olmalı.")
        elif e.get("stage") is None:
            satirlar.append(
                "Red PREFLIGHT'ta **değil**, bir alt katmanda olmalı — "
                "asıl ölçülen bu."
            )
        for parca in e.get("reason_contains", []):
            satirlar.append(f"Red gerekçesinde `{parca}` geçmeli.")
        return satirlar

    if e.get("engine_limit"):
        satirlar.append(
            "**Hesaplanamamalı** — ve bu doğru davranıştır. Sistem çökmeden, "
            "uydurma bir sayı vermeden, iki motor kademesini de denediğini "
            "söyleyerek durmalı."
        )
        return satirlar

    # Katılaşma vakaları: denge değil yol. Ölçütleri de farkli, ve "faz
    # miktarları 1'e toplamalı" gibi denge ölçütleri buraya hiç uymuyor.
    if case.get("tool") == "calculate_scheil_solidification":
        if e.get("completed") is True:
            satirlar.append(
                "Katılaşma **sonuna kadar gitmeli** (`completed: true`)."
            )
        elif e.get("completed") is False:
            satirlar.append(
                "Katılaşma bu sistemde sonuna kadar **gitmiyor** — ve ölçüt "
                "bunu düzeltmek değil, **doğru söylemek**: `completed: false` "
                "dönmeli, kalan sıvı oranı raporlanmalı. Yarım kalmış bir "
                "eğriyi tam gibi sunmak bu vakayı düşürür."
            )
        if e.get("max_final_liquid_fraction") is not None:
            satirlar.append(
                f"Sonda kalan sıvı **{e['max_final_liquid_fraction']:.1%}"
                "'i geçmemeli**."
            )
        if e.get("solid_phases"):
            satirlar.append("Katılaşma sırasında şu faz(lar) oluşmalı: "
                            + ", ".join(f"`{p}`" for p in e["solid_phases"]))
        istek = case["arguments"]["elements_composition"]
        olcek = sum(istek.values()) or 1
        for element, en_az in (e.get("segregation") or {}).items():
            nominal = istek.get(element, 0) / olcek
            satirlar.append(
                f"**Segregasyon:** son sıvıda `{element}` nominal "
                f"{nominal:.4g} değerinin üzerine çıkmalı, en az {en_az:.4g}. "
                "Scheil'in ölçtüğü şey bu."
            )
        satirlar.append("Sıvı çizgisi (liquidus) bulunmalı.")
        return satirlar

    # Faz diyagramı: çıktı tablo değil eğri kümesi, ölçütü de değişmez
    # sıcaklıklar. "Faz miktarları 1'e toplamalı" burada anlamsız.
    if case.get("tool") == "calculate_phase_diagram":
        if e.get("phases"):
            satirlar.append("Diyagramda şu faz(lar) görünmeli: "
                            + ", ".join(f"`{p}`" for p in e["phases"]))
        tol = e.get("invariant_tolerance_K", 2.0)
        for T in e.get("invariant_temperatures_K", []):
            satirlar.append(
                f"**{T:g} K** civarında (± {tol:g} K) bir değişmez tepkime "
                "bulunmalı — ötektik, ötektoid ya da peritektik."
            )
        if e.get("min_boundaries"):
            satirlar.append(
                f"En az **{e['min_boundaries']} faz sınırı** izlenmeli."
            )
        satirlar.append(
            "Her sınır **en az iki fazlı** olmalı — tanım gereği bir sınır, "
            "fazların buluştuğu yerdir."
        )
        return satirlar

    if e.get("phases"):
        satirlar.append("Şu faz(lar) sonuçta bulunmalı: "
                        + ", ".join(f"`{p}`" for p in e["phases"]))
    if e.get("phase_count") is not None:
        satirlar.append(f"Toplam **{e['phase_count']} faz** olmalı.")
    # Bileşim ekseni ölçütleri. Bir taramada asıl bilgi hangi fazların
    # göründüğü değil, hangi SIRAYLA göründüğü — o yüzden bu satırlar
    # soru listesinde de görünmeli, yoksa vakanın ne ölçtüğü kaybolur.
    for once, sonra in e.get("phase_order", []):
        satirlar.append(
            f"Eksen boyunca `{once}` **`{sonra}`'den önce** görünmeli."
        )
    if e.get("phases_at_start"):
        satirlar.append("Eksenin başında: "
                        + ", ".join(f"`{p}`" for p in e["phases_at_start"]))
    if e.get("phases_at_end"):
        satirlar.append("Eksenin sonunda: "
                        + ", ".join(f"`{p}`" for p in e["phases_at_end"]))
    if case.get("tool") == "calculate_isothermal_section":
        satirlar.append(
            "İstenen eksen aralığının **iki ucu da** sonuçta olmalı."
        )
    if e.get("max_failed_fraction") is not None:
        satirlar.append(
            f"Çözülemeyen nokta oranı %{e['max_failed_fraction'] * 100:.0f}'i "
            "geçmemeli."
        )
    satirlar.append("Faz miktarları **1'e toplamalı**.")

    if e.get("mass_balance"):
        satirlar.append(
            "**Kütle dengesi:** her element için "
            "`Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı."
        )
    if e.get("elements_present"):
        satirlar.append(
            "İstenen **her element** en az bir fazın bileşiminde görünmeli. "
            "Görünmeyen bir element hesaba hiç girmemiştir."
        )
    for faz, oran in (e.get("stoichiometry") or {}).items():
        ad = STOKIYOMETRI_ADI.get(round(oran, 6), f"{oran:.4f}")
        satirlar.append(
            f"`{faz}` fazının karbon oranı **{ad} = {oran:.4f}** olmalı "
            "(formülden gelir, motordan değil)."
        )
    if e.get("gibbs_energy_J"):
        ref = e["gibbs_energy_J"]
        satirlar.append(
            f"Gibbs enerjisi **{ref['value']:,.3f} J** olmalı "
            f"(± {ref['tolerance']}). Elle doğrulanmış referans."
        )
    if e.get("backend_used"):
        satirlar.append(f"Kullanılan motor `{e['backend_used']}` olmalı.")
    return satirlar


def main():
    out = []
    out.append("# Kıyaslama Soruları\n")
    out.append(
        "Her soru için üç şey var: **soru metni**, **neyi sınadığı** ve "
        "**beklenen cevap**.\n\n"
        "Beklenen cevabın her maddesi hesap makinesiyle kontrol edilebilir. "
        "Termodinamik bilgisi gerektiren tek bir ölçüt yok — kütle korunumu "
        "ve stokiyometri, motorun kendi çıktısından bağımsız iki bağımsız "
        "denetimdir.\n\n"
        "Zorluk, cümlenin kulağa nasıl geldiğine göre değil, sistemin başına "
        "ne geldiğine göre belirlendi:\n\n"
        "- **kolay** — tek araç, motor ilk denemede yakınsıyor\n"
        "- **orta** — biri var: motor kademe atlıyor, faz geçişi var, "
        "önce arama gerekiyor, ya da istek reddedilmeli\n"
        "- **zor** — ikisi ya da fazlası var: motor kısmen başarısız, "
        "bileşim kümeleri, hiç denenmemiş sistem sınıfı\n\n"
        "Her soruyu **temiz bir oturumda** sor. Aynı oturumda arka arkaya "
        "sormak, modelin kendi önceki cevabını görmesine yol açar; o zaman "
        "ölçülen şey sistem değil konuşma olur.\n"
    )

    toplam = 0
    for harf, baslik, alan in GRUPLAR:
        grup = getattr(cases, alan, [])
        if not grup:
            continue
        sayim = {z: sum(1 for c in grup if c["zorluk"] == z)
                 for z in ("kolay", "orta", "zor")}
        out.append(f"\n---\n\n# {harf} · {baslik}\n")
        out.append(
            f"*{len(grup)} soru — kolay {sayim['kolay']}, "
            f"orta {sayim['orta']}, zor {sayim['zor']}*\n"
        )
        for sira, case in enumerate(grup, 1):
            toplam += 1
            out.append(f"\n## {harf}{sira} · {case['id']}")
            out.append(f"*zorluk: {case['zorluk']}*\n")
            out.append("**Soru**")
            out.append("```")
            out.append(case["soru"])
            out.append("```\n")
            out.append("**Neyi sınıyor**")
            out.append(case["olcum"] + "\n")
            out.append("**Beklenen cevap**")
            for satir in beklenen_metni(case):
                out.append(f"- {satir}")
            out.append("")

    out.append(f"\n---\n\n**Toplam: {toplam} soru.**\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
