# misura_euristiche.py — PROTOTIPO throwaway (ticket 05)
# Misura suggerisci_campi() sui layer di esempio e produce la tabella campo -> match-rate.
#
# ESECUZIONE (headless):
#   "C:/Program Files/QGIS 3.44.4/apps/Python312/python.exe" con
#   PYTHONPATH=".../apps/qgis/python" misura_euristiche.py
#
# OUTPUT: tabella-match-rate.md (+ .json) in questa cartella.
# Gira in DUE modalita': con e senza cartella base (prima/dopo che il wizard la chiede).

import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

ESEMPI = os.path.join(BASE, "esempi")
GPKG = os.path.join(ESEMPI, "discovery_esempi.gpkg")
FOTO = os.path.join(ESEMPI, "foto")
ATTESI = os.path.join(ESEMPI, "attesi.json")
MD = os.path.join(BASE, "tabella-match-rate.md")
JSON = os.path.join(BASE, "tabella-match-rate.json")


def _carica_layer(nome):
    from qgis.core import QgsVectorLayer
    lyr = QgsVectorLayer(f"{GPKG}|layername={nome}", nome, "ogr")
    assert lyr.isValid(), f"layer non caricato: {nome}"
    return lyr


def _esito(campo, verita):
    if campo in verita["attesi"]:
        return "atteso"
    if campo in verita["trappole"]:
        return "trappola"
    if campo in verita["trappole_soft_ammesse"]:
        return "trappola (soft ok)"
    return "–"


def _conta(righe, verita):
    """Precision/recall rispetto alla verita' attesa, per livello stretto (A+B) e soft (C)."""
    strict = {r.campo for r in righe if r.livello in "AB"}
    soft = {r.campo for r in righe if r.livello == "C"}
    attesi = set(verita["attesi"])
    trappole = set(verita["trappole"])
    soft_ok = set(verita.get("trappole_soft_ammesse", []))
    return {
        "attesi": sorted(attesi),
        "strict": sorted(strict),
        "soft": sorted(soft),
        "tp_strict": sorted(attesi & strict),
        "fn": sorted(attesi - strict - soft),
        "fn_soft": sorted(attesi - strict),          # trovati solo come C (o non trovati)
        "fp_strict": sorted(strict & trappole),      # trappole preselezionate = errore
        "c_attese": sorted(soft & (trappole & soft_ok)),
        "c_extra": sorted(soft & (trappole - soft_ok)),
        "c_neutre": sorted(soft - trappole - attesi),
    }


def main():
    from qgis.core import QgsApplication
    sys.path.insert(0, os.path.join(BASE))
    from suggerisci_campi import suggerisci_campi, tabella_markdown

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    app = QgsApplication([], False)
    QgsApplication.setPrefixPath(r"C:\Program Files\QGIS 3.44.4\apps\qgis", True)
    QgsApplication.initQgis()
    esito = 1
    try:
        # Fixture idempotenti: i file foto finti e il GPKG stanno fuori dal git
        # (.gitignore esclude *.jpg/png/pdf), quindi si rigenerano da soli se mancano.
        if not os.path.exists(GPKG) or not os.path.isdir(FOTO):
            sys.path.insert(0, ESEMPI)
            import genera_esempi
            genera_esempi.genera_tutto()
            print("fixture rigenerate (esempi/foto + discovery_esempi.gpkg)")

        with open(ATTESI, encoding="utf-8") as f:
            verita_per_layer = json.load(f)

        modalita = [
            ("Senza cartella base (discovery sintattica)", None),
            (f"Con cartella base = esempi/foto", FOTO),
        ]
        blocchi, dati = [], {"cartella_base": FOTO, "modalita": {}}
        for etichetta, cartella in modalita:
            righe_per_layer = {}
            for nome, verita in verita_per_layer.items():
                lyr = _carica_layer(nome)
                righe = suggerisci_campi(lyr, cartella_base=cartella)
                righe_per_layer[nome] = (righe, verita)
            dati["modalita"][etichetta] = {
                n: {"righe": [r.dict() for r in v[0]], "verifica": _conta(v[0], v[1])}
                for n, v in righe_per_layer.items()}
            blocchi.append((etichetta, righe_per_layer))

        # ---------------------------------------------------------- markdown
        md = ["# Ticket 05 — tabella campo → match-rate (auto-discovery campi foto)", "",
              "Generato da `misura_euristiche.py` su `esempi/discovery_esempi.gpkg` "
              "(12 feature per layer, valori costruiti sulle forme reali dei due script).", "",
              "Legenda livelli: **A** = file trovati nella cartella base (preselezionato) · "
              "**B** = valori con estensione, non verificati su disco (preselezionato con avviso) · "
              "**C** = solo il nome suggerisce (mostrato, NON preselezionato) · "
              "**D** = scartato.", "",
              "Legenda colonne: `esiste%` = quota di valori non nulli risolti a un file reale · "
              "`ext%` = quota con estensione di file · `multi%` = valori con più file · "
              "`guid%/num%/remoto%` = quote dei segnali che fanno scartare.", ""]

        for etichetta, righe_per_layer in blocchi:
            md += [f"## {etichetta}", ""]
            for nome, (righe, verita) in righe_per_layer.items():
                md += tabella_markdown(righe, titolo=f"`{nome}`").split("\n") + [""]

        # ---------------------------------------------------------- verifica
        md += ["## Verifica contro la verità attesa", "",
               "`atteso` = campo che i due script userebbero davvero. "
               "`trappola` = campo che NON deve essere preselezionato.", ""]
        for etichetta, righe_per_layer in blocchi:
            md += [f"### {etichetta}", "",
                   "| layer | campo | esito atteso | livello | match-rate (esiste/ext) |",
                   "|---|---|---|---|---|"]
            for nome, (righe, verita) in righe_per_layer.items():
                for r in righe:
                    md.append("| `{}` | {} | {} | **{}** | {:.0%} / {:.0%} |".format(
                        nome, r.campo, _esito(r.campo, verita), r.livello,
                        r.esiste_rate, r.ext_rate))
            md.append("")
            tot = {"tp": 0, "attesi": 0, "fp": 0, "fn": 0, "c_extra": 0}
            for nome, (righe, verita) in righe_per_layer.items():
                c = _conta(righe, verita)
                tot["tp"] += len(c["tp_strict"])
                tot["attesi"] += len(c["attesi"])
                tot["fp"] += len(c["fp_strict"])
                tot["fn"] += len(c["fn_soft"])
                tot["c_extra"] += len(c["c_extra"])
            md += [f"- Attesi trovati in A+B: **{tot['tp']}/{tot['attesi']}** · "
                   f"falsi positivi in A+B: **{tot['fp']}** · "
                   f"attesi non preselezionati: **{tot['fn']}** (di cui alcuni in C) · "
                   f"trappole in C (non preselezionate): **{tot['c_extra']}**", ""]

        with open(MD, "w", encoding="utf-8") as f:
            f.write("\n".join(md))
        with open(JSON, "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False, indent=2)
        print("\n".join(md))
        print(f"\nScritti: {MD}  e  {JSON}")
        esito = 0
    except BaseException:
        import traceback
        traceback.print_exc()
    finally:
        # QGIS headless su Windows va in segfault nel teardown degli OGR data source:
        # usciamo con os._exit dopo il flush (niente cleanup Qt, exit code esplicito).
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass
        os._exit(esito)


if __name__ == "__main__":
    main()
