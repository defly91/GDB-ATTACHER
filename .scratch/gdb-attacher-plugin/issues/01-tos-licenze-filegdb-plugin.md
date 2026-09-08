Map: [map](../map.md)
Type: research (AFK)
Status: done
Blocked by: none
Labels: wayfinder:research

## Answer (context pointer)

Verdetto: **no violazioni** se: solo driver GDAL OpenFileGDB, licenza plugin
GPLv2+, dipendenze dichiarate in About, niente binari. Dettagli + fonti:
[research-tos.md](../research-tos.md). Branch: `research/tos-licenze` (throwaway).

## Question

Pubblicando un plugin QGIS che scrive attachment in un FileGDB Esri violiamo qualche TOS, licenza o regola del repository plugin QGIS?

Indagare: licenza Esri FileGDB SDK vs driver GDAL OpenFileGDB (lettura/scrittura, limiti noti su attachments), regole ufficiali repo plugin QGIS (GPL2 compatibilità, librerie esterne ammesse), eventuali TOS Esri su reverse-engineering del formato GDB. Output atteso: sì/no con fonti + vincoli (es. solo OpenFileGDB, niente SDK chiuso, licenza plugin consigliata).
