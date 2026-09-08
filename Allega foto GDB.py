import os
import uuid
from qgis.PyQt.QtCore import QByteArray
from qgis.core import QgsProject, QgsFeature, edit

# Radice comune del percorso immagini
foto_base_path = r'C:\Users\Stefano\OneDrive - Tae Srl\Desktop\Lavori\AcuqeVeronesi\Consegna impianti 3\Foto'

# Lista dei layer da elaborare
layers_config = [
    {
        'layer_name': 'Ril_ApFp_contatore',
        'foto_fields': ['filefoto'],
        'subpath': ''
    },
    {
        'layer_name': 'Ril_ApFp_sottosuolo',
        'foto_fields': ['FILEFOTO'],
        'subpath': ''
    },
    {
        'layer_name': 'Ril_ApFp_superficie',
        'foto_fields': ['FOTO_EST', 'FOTO_INT'],
        'subpath': ''
    }
]

# Statistiche
stat = {}

for config in layers_config:
    layer_name = config['layer_name']
    foto_fields = config['foto_fields']
    subfolder = os.path.join(foto_base_path, config['subpath'])

    layer = QgsProject.instance().mapLayersByName(layer_name)[0]
    attach_layer = QgsProject.instance().mapLayersByName(layer_name + '__ATTACH')[0]

    campo_globalid = 'GLOBALID'
    esistenti = set()

    for feat in attach_layer.getFeatures():
        rel = feat['REL_GLOBALID']
        nome = feat['ATT_NAME']
        esistenti.add((rel, nome))

    aggiunti = 0
    duplicati = 0
    saltati = 0

    with edit(attach_layer):
        for feature in layer.getFeatures():
            rel_globalid = feature[campo_globalid]
            if not rel_globalid:
                saltati += 1
                continue

            for campo_foto in foto_fields:
                nomefile_base = feature[campo_foto]
                if not nomefile_base:
                    continue

                nome_file_completo = nomefile_base # + '.jpg'
                percorso_foto = os.path.join(subfolder, nome_file_completo)

                if not os.path.isfile(percorso_foto):
                    print(f"[MANCANTE] {layer_name}: {percorso_foto}")
                    saltati += 1
                    continue

                if (rel_globalid, nome_file_completo) in esistenti:
                    print(f"[DUPLICATO] {layer_name}: {rel_globalid} - {nome_file_completo}")
                    duplicati += 1
                    continue

                with open(percorso_foto, 'rb') as f:
                    data_binaria = f.read()

                dimensione = len(data_binaria)
                nuovo_globalid = str(uuid.uuid4()).upper()

                nuova_feature = QgsFeature(attach_layer.fields())
                nuova_feature['GLOBALID'] = nuovo_globalid
                nuova_feature['REL_GLOBALID'] = rel_globalid
                nuova_feature['CONTENT_TYPE'] = 'image/jpeg'
                nuova_feature['DATA_SIZE'] = dimensione
                nuova_feature['ATT_NAME'] = nome_file_completo
                nuova_feature['DATA'] = QByteArray(data_binaria)

                attach_layer.addFeature(nuova_feature)
                esistenti.add((rel_globalid, nome_file_completo))
                aggiunti += 1

    # Salvataggio statistiche
    stat[layer_name] = {
        'aggiunti': aggiunti,
        'duplicati': duplicati,
        'saltati': saltati
    }

# Riepilogo
print("\n📊 RIEPILOGO COMPLETATO:")
for layer, dati in stat.items():
    print(f"🔹 {layer}:")
    print(f"    ➕ Allegati aggiunti: {dati['aggiunti']}")
    print(f"    🔁 Duplicati ignorati: {dati['duplicati']}")
    print(f"    ⚠️ Saltati (foto mancante o dati nulli): {dati['saltati']}")
