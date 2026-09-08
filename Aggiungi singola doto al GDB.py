import os
import uuid

from qgis.PyQt.QtCore import QByteArray
from qgis.PyQt.QtWidgets import QInputDialog, QMessageBox, QFileDialog
from qgis.PyQt.QtGui import QCursor
from qgis.PyQt.QtCore import Qt

from qgis.core import QgsProject, QgsFeature, edit
from qgis.gui import QgsMapToolIdentify, QgsMapTool


# -------------------------------
# Utility: trova campo ignorando maiuscole/minuscole
# -------------------------------
def find_field_ci(layer, preferred_names):
    """
    Restituisce il nome del campo presente nel layer che matcha uno dei preferred_names
    ignorando maiuscole/minuscole. Se non trovato, ritorna None.
    """
    existing = [f.name() for f in layer.fields()]
    existing_lut = {name.lower(): name for name in existing}

    for n in preferred_names:
        key = str(n).lower()
        if key in existing_lut:
            return existing_lut[key]
    return None


# -------------------------------
# Utility: normalizza GUID
# -------------------------------
def normalize_guid(g):
    """
    Ritorna GUID in formato 'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX' uppercase (senza graffe).
    Accetta anche '{GUID}' e lo normalizza.
    """
    if g is None:
        return None
    s = str(g).strip()
    if not s:
        return None
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1]
    s = s.strip()
    if not s:
        return None
    return s.upper()


def with_braces(guid_no_braces):
    if guid_no_braces is None:
        return None
    return "{" + str(guid_no_braces).upper() + "}"


# -------------------------------
# Utility: mime type da estensione
# -------------------------------
def guess_content_type(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    if ext in (".tif", ".tiff"):
        return "image/tiff"
    if ext == ".pdf":
        return "application/pdf"
    return "application/octet-stream"


# ------------------------------------
# Map tool: click su feature e inserisce allegato
# ------------------------------------
class AddAttachmentByClickTool(QgsMapTool):
    def __init__(self, canvas, layer, attach_layer, gid_field_main, attach_fields, mode,
                 base_folder=None, foto_field=None, manual_file=None):
        super().__init__(canvas)
        self.canvas = canvas
        self.layer = layer
        self.attach_layer = attach_layer
        self.gid_field_main = gid_field_main        # es: "GlobalID"
        self.attach_fields = attach_fields          # dict con nomi reali campi attach
        self.mode = mode                            # "FIELD" oppure "MANUAL"
        self.base_folder = base_folder
        self.foto_field = foto_field
        self.manual_file = manual_file
        self.prev_tool = None

        self.ident = QgsMapToolIdentify(canvas)
        self.setCursor(QCursor(Qt.CrossCursor))

        # Cache duplicati: (REL_GLOBALID_con_graffe, ATT_NAME)
        self._existing = set()
        rel_f = self.attach_fields["REL_GLOBALID"]
        name_f = self.attach_fields["ATT_NAME"]

        for f in self.attach_layer.getFeatures():
            rel_raw = f[rel_f]
            rel_norm = normalize_guid(rel_raw)
            rel_br = with_braces(rel_norm) if rel_norm else None

            att_name = f[name_f]
            att_name = str(att_name) if att_name is not None else ""

            if rel_br:
                self._existing.add((rel_br, att_name))

        print(f"[DEBUG] Cache duplicati iniziale: {len(self._existing)} coppie (REL_GLOBALID, ATT_NAME)")
        print(f"[DEBUG] Campo GUID layer principale: {self.gid_field_main}")
        print(f"[DEBUG] Campi attach risolti: {self.attach_fields}")

    def activate(self):
        super().activate()
        print(f"👉 Modalità click attiva. Clicca una feature del layer: '{self.layer.name()}'")

    def deactivate(self):
        super().deactivate()
        print("✅ Tool disattivato.")

    def _restore_previous_tool(self):
        try:
            if self.prev_tool:
                self.canvas.setMapTool(self.prev_tool)
        except Exception:
            pass

    def canvasReleaseEvent(self, event):
        # Identifica la feature cliccata sul layer scelto
        results = self.ident.identify(
            event.x(),
            event.y(),
            [self.layer],
            QgsMapToolIdentify.TopDownStopAtFirst
        )

        if not results:
            QMessageBox.warning(None, "Nessuna feature", "Non ho trovato nessuna feature sotto al click.")
            return

        feat = results[0].mFeature

        try:
            self._process_feature(feat)
        except Exception as e:
            QMessageBox.critical(None, "Errore", f"Errore durante l'aggiunta allegato:\n{e}")
            print("❌ Errore:", e)

        # Dopo un inserimento (o tentativo), torna allo strumento precedente
        self._restore_previous_tool()

    def _process_feature(self, feature):
        # --- Leggi GlobalID dal layer principale (case giusto) ---
        raw_gid = feature.attribute(self.gid_field_main)
        gid_norm = normalize_guid(raw_gid)
        rel_globalid = with_braces(gid_norm)

        print(f"[DEBUG] raw {self.gid_field_main} = {raw_gid} | normalized = {gid_norm} | with braces = {rel_globalid}")

        if not rel_globalid:
            raise Exception(f"La feature non ha {self.gid_field_main} valorizzato (nullo/vuoto).")

        # --- Determina file da allegare ---
        if self.mode == "FIELD":
            if not self.foto_field:
                raise Exception("Modalità FIELD ma foto_field non impostato.")
            if not self.base_folder:
                raise Exception("Modalità FIELD ma base_folder non impostata.")

            filename = feature.attribute(self.foto_field)
            print(f"[DEBUG] campo foto '{self.foto_field}' = {filename}")

            if filename is None or str(filename).strip() == "":
                raise Exception(f"Il campo '{self.foto_field}' è nullo/vuoto per questa feature.")

            att_name = str(filename).strip()
            full_path = os.path.join(self.base_folder, att_name)

        elif self.mode == "MANUAL":
            if not self.manual_file:
                raise Exception("Modalità MANUAL ma manual_file non impostato.")
            full_path = self.manual_file
            att_name = os.path.basename(full_path)

        else:
            raise Exception(f"Modalità sconosciuta: {self.mode}")

        # --- Check file ---
        if not os.path.isfile(full_path):
            raise Exception(f"File non trovato:\n{full_path}")

        # --- Duplicato? (REL_GLOBALID con graffe + ATT_NAME) ---
        if (rel_globalid, att_name) in self._existing:
            QMessageBox.information(
                None,
                "Duplicato",
                f"Esiste già un allegato con:\nREL_GLOBALID={rel_globalid}\nATT_NAME={att_name}\n\nNessuna modifica fatta."
            )
            print(f"[DUPLICATO] REL_GLOBALID={rel_globalid} ATT_NAME={att_name}")
            return

        # --- Leggi bytes ---
        with open(full_path, "rb") as f:
            data_binaria = f.read()

        dimensione = len(data_binaria)
        nuovo_globalid = str(uuid.uuid4()).upper()
        content_type = guess_content_type(full_path)

        # --- Scrivi su attach usando i nomi reali dei campi ---
        f_gid = self.attach_fields["GLOBALID"]        # tipicamente "GLOBALID"
        f_rel = self.attach_fields["REL_GLOBALID"]    # tipicamente "REL_GLOBALID"
        f_ct  = self.attach_fields["CONTENT_TYPE"]    # tipicamente "CONTENT_TYPE"
        f_ds  = self.attach_fields["DATA_SIZE"]       # tipicamente "DATA_SIZE"
        f_nm  = self.attach_fields["ATT_NAME"]        # tipicamente "ATT_NAME"
        f_dt  = self.attach_fields["DATA"]            # tipicamente "DATA"

        with edit(self.attach_layer):
            nuova = QgsFeature(self.attach_layer.fields())
            nuova[f_gid] = nuovo_globalid
            nuova[f_rel] = rel_globalid
            nuova[f_ct]  = content_type
            nuova[f_ds]  = dimensione
            nuova[f_nm]  = att_name
            nuova[f_dt]  = QByteArray(data_binaria)

            ok = self.attach_layer.addFeature(nuova)

        if not ok:
            raise Exception("addFeature() ha restituito False (feature non aggiunta).")

        self._existing.add((rel_globalid, att_name))

        print(f"[OK] Aggiunto: REL_GLOBALID={rel_globalid} ATT_NAME={att_name} SIZE={dimensione} CONTENT_TYPE={content_type}")
        QMessageBox.information(
            None,
            "OK",
            f"✅ Allegato aggiunto!\n\nREL_GLOBALID: {rel_globalid}\nATT_NAME: {att_name}\nDATA_SIZE: {dimensione} bytes"
        )


# -------------------------------
# Avvio procedura
# -------------------------------
canvas = iface.mapCanvas()
project = QgsProject.instance()

# 1) scegli layer vettoriale
vector_layers = [lyr for lyr in project.mapLayers().values() if lyr.type() == lyr.VectorLayer]
layer_names = [lyr.name() for lyr in vector_layers]

if not layer_names:
    QMessageBox.warning(None, "Nessun layer", "Non ci sono layer vettoriali nel progetto.")
    raise Exception("Nessun layer vettoriale.")

layer_name, ok = QInputDialog.getItem(None, "Seleziona layer", "Layer:", layer_names, 0, False)
if not ok or not layer_name:
    print("⏹️ Annullato: selezione layer.")
    raise Exception("Annullato.")

layer = project.mapLayersByName(layer_name)[0]

# 2) risolvi campo GlobalID (principale) in modo robusto
gid_field_main = find_field_ci(layer, ["GlobalID", "GLOBALID", "globalid"])
if not gid_field_main:
    QMessageBox.critical(None, "Campo mancante",
                         f"Il layer '{layer.name()}' non ha il campo GlobalID/GLOBALID.")
    raise Exception("Campo GlobalID mancante nel layer scelto.")

# 3) trova attach layer
attach_name = layer.name() + "__ATTACH"
attach_list = project.mapLayersByName(attach_name)
if not attach_list:
    QMessageBox.critical(None, "Attach mancante",
                         f"Non trovo il layer attach '{attach_name}'.\nCaricalo nel progetto o verifica il nome.")
    raise Exception("Attach layer mancante.")
attach_layer = attach_list[0]

# 4) risolvi i campi attach (case-insensitive)
attach_fields = {}
attach_fields["GLOBALID"]      = find_field_ci(attach_layer, ["GLOBALID"])
attach_fields["REL_GLOBALID"]  = find_field_ci(attach_layer, ["REL_GLOBALID"])
attach_fields["CONTENT_TYPE"]  = find_field_ci(attach_layer, ["CONTENT_TYPE"])
attach_fields["DATA_SIZE"]     = find_field_ci(attach_layer, ["DATA_SIZE"])
attach_fields["ATT_NAME"]      = find_field_ci(attach_layer, ["ATT_NAME"])
attach_fields["DATA"]          = find_field_ci(attach_layer, ["DATA"])

missing = [k for k, v in attach_fields.items() if not v]
if missing:
    QMessageBox.critical(None, "Campi attach mancanti",
                         f"Nel layer '{attach_layer.name()}' mancano i campi richiesti: {missing}")
    raise Exception(f"Campi mancanti in attach: {missing}")

# 5) scegli modalità
mode_label, ok = QInputDialog.getItem(
    None,
    "Modalità allegato",
    "Come vuoi scegliere il file da allegare?",
    ["Da campo foto (attributo)", "Selezione manuale file"],
    0,
    False
)
if not ok:
    print("⏹️ Annullato: scelta modalità.")
    raise Exception("Annullato.")

mode_key = "FIELD" if "campo" in mode_label.lower() else "MANUAL"

base_folder = None
foto_field = None
manual_file = None

if mode_key == "FIELD":
    # scegli campo foto
    fields = [f.name() for f in layer.fields()]
    foto_field, ok = QInputDialog.getItem(None, "Campo foto", "Seleziona il campo che contiene il nome file:", fields, 0, False)
    if not ok or not foto_field:
        print("⏹️ Annullato: selezione campo foto.")
        raise Exception("Annullato.")

    # scegli cartella base
    base_folder = QFileDialog.getExistingDirectory(None, "Seleziona cartella base delle foto", "")
    if not base_folder:
        print("⏹️ Annullato: selezione cartella base.")
        raise Exception("Annullato.")

else:
    # scegli file manualmente
    manual_file, _ = QFileDialog.getOpenFileName(
        None,
        "Seleziona file da allegare",
        "",
        "Tutti i file (*.*);;Immagini (*.jpg *.jpeg *.png *.tif *.tiff);;PDF (*.pdf)"
    )
    if not manual_file:
        print("⏹️ Annullato: selezione file.")
        raise Exception("Annullato.")

# 6) attiva tool di click
tool = AddAttachmentByClickTool(
    canvas=canvas,
    layer=layer,
    attach_layer=attach_layer,
    gid_field_main=gid_field_main,
    attach_fields=attach_fields,
    mode=mode_key,
    base_folder=base_folder,
    foto_field=foto_field,
    manual_file=manual_file
)

tool.prev_tool = canvas.mapTool()
canvas.setMapTool(tool)

QMessageBox.information(
    None,
    "Istruzioni",
    f"Ora clicca una feature del layer:\n{layer.name()}\n\nDopo l'inserimento, tornerò allo strumento precedente."
)
print("🚀 Pronto. Clicca una feature...")