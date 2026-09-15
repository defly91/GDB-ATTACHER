# fake_qgis.py — finto QGIS per i test (nessun QGIS/GDAL/osgeo installato).
#
# PERCHE' ESISTE
# Su questa VM e in CI (GitHub Actions ubuntu-latest) non c'e' QGIS ne' GDAL.
# Il codice del plugin importa `qgis.core`, `qgis.PyQt.QtCore`, `qgis.gui` ecc.:
# senza quelle import qualsiasi test fallisce in raccolta. Qui costruiamo moduli
# finti e li iniettiamo in `sys.modules` PRIMA che il codice del plugin venga
# importato (lo fa `tests/conftest.py`, che viene caricato per primo da pytest).
#
# PROGETTO: e' volutamente GENERICO, non conosce i nomi interni del plugin.
#   - le classi note (QgsVectorLayer, QgsFeature, QMessageBox...) sono esplicite;
#   - qualunque nome sconosciuto di qgis.* diventa uno stub class-level creato
#     al volo, quindi un import non previsto non rompe la raccolta.
#
# COSA NON FA: non tocca il disco del GDB, non parla con OGR, non renderizza QML.
# Serve a testare logica pura, wizard, naming, dedup, risoluzione file, packaging.
#
# USO
#   from fake_qgis import install, crea_layer_sorgente, crea_layer_attach, carica
#   install()                       # idempotente
#   import qgis.core as qc          # ora importa i finti
#   lyr = crea_layer_sorgente()     # layer con GLOBALID + campo foto
#   mod = carica("gdb_attacher/naming.py")   # importa un file del plugin per percorso
#
# Nella quasi totalita' dei casi non serve chiamare `install()`: ci pensa
# `tests/conftest.py`, che espone anche le fixture `progetto`, `layer_sorgente`,
# `layer_attach`, `cartella_foto`, `carica` e `qcore`.

from __future__ import annotations

import importlib.util
import os
import sys
import types
from contextlib import contextmanager

__all__ = [
    "install", "disinstalla", "azzera_tutto",
    "FakeLayer", "FakeFeature", "FakeField", "FakeFields", "FakeProject",
    "NULL", "QByteArray", "Qt", "QMetaType", "QgsMapLayerType",
    "crea_feature", "crea_layer_sorgente", "crea_layer_attach",
    "registra_sorgente", "carica", "SCHEMA_SORGENTE", "SCHEMA_ATTACH",
    "risposte", "REGISTRO_DIALOGHI",
]

# ---------------------------------------------------------------------------
# Stub generici


def _finto_callable(nome, valore=None):
    def _f(*args, **kwargs):
        return valore
    _f.__name__ = nome
    return _f


def _crea_stub(nome):
    """Classe finta creata al volo: istanziabile e sottoclassabile."""
    return type(str(nome), (_Qualsiasi,), {})


class _Qualsiasi:
    """Base permissiva: gli attributi ignoti diventano finti metodi no-op.

    Gli attributi "dunder" restano esterni a questo meccanismo per non rompere
    copy/pickle/isinstance.
    """

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, nome):
        if nome.startswith("__"):
            raise AttributeError(nome)
        return _finto_callable(nome)


_CONTATORE_INTERI = [1000]


def _nuovo_intero():
    _CONTATORE_INTERI[0] += 1
    return _CONTATORE_INTERI[0]


class _MetaclasseEnum(type):
    """Metaclasse che crea al volo le costanti enum non dichiarate."""

    def __getattr__(cls, nome):
        if nome.startswith("__"):
            raise AttributeError(nome)
        valore = _nuovo_intero()
        setattr(cls, nome, valore)
        return valore


class _EnumAuto(metaclass=_MetaclasseEnum):
    """Enum finto: costanti note dichiarate, le altre nascono on demand."""


# ---------------------------------------------------------------------------
# QtCore


class QByteArray:
    """QByteArray finta: accetta bytes/bytearray/str e si confronta coi bytes."""

    def __init__(self, dati=b""):
        if isinstance(dati, QByteArray):
            dati = dati._dati
        elif isinstance(dati, str):
            dati = dati.encode("utf-8")
        elif isinstance(dati, (bytes, bytearray, memoryview)):
            dati = bytes(dati)
        else:
            dati = bytes(dati)
        self._dati = bytes(dati)

    def data(self):
        return self._dati

    def toBase64(self):
        import base64
        return QByteArray(base64.b64encode(self._dati))

    def size(self):
        return len(self._dati)

    def isEmpty(self):
        return len(self._dati) == 0

    def __len__(self):
        return len(self._dati)

    def __bytes__(self):
        return self._dati

    def __eq__(self, altro):
        if isinstance(altro, QByteArray):
            return self._dati == altro._dati
        if isinstance(altro, (bytes, bytearray)):
            return self._dati == bytes(altro)
        return NotImplemented

    def __hash__(self):
        return hash(self._dati)

    def __repr__(self):
        return "QByteArray(%r)" % (self._dati[:32],)


class QMetaType:
    class Type(_EnumAuto):
        Bool = 1
        Int = 2
        LongLong = 4
        Double = 6
        QChar = 11
        QString = 10
        QByteArray = 12
        QDate = 14
        QTime = 15
        QDateTime = 16
        Float = 38


class QVariant:
    """Solo per compatibilita': il vecchio enum Qt usato da script piu' vecchi."""

    class Type(_EnumAuto):
        Invalid = 0
        Bool = 1
        Int = 2
        Double = 6
        QString = 10
        String = 10
        QByteArray = 12
        Date = 14
        DateTime = 16

    def __init__(self, valore=None):
        self._valore = valore

    def value(self):
        return self._valore

    def isNull(self):
        return self._valore is None

    def __repr__(self):
        return "QVariant(%r)" % (self._valore,)


class _QtFinto:
    """Namespace Qt: costanti note esplicite, altre generate on demand."""

    CrossCursor = 2
    ArrowCursor = 0
    WaitCursor = 3
    OpenHandCursor = 14
    LeftButton = 1
    RightButton = 2
    NoButton = 0
    UserRole = 256
    DisplayRole = 0
    EditRole = 2
    CheckStateRole = 10
    Checked = 2
    Unchecked = 0
    PartiallyChecked = 1
    AlignLeft = 1
    AlignRight = 2
    AlignCenter = 4
    Horizontal = 1
    Vertical = 2
    ItemIsEnabled = 1
    ItemIsSelectable = 2
    KeepAspectRatio = 1
    SmoothTransformation = 4

    def __getattr__(self, nome):
        if nome.startswith("__"):
            raise AttributeError(nome)
        valore = _nuovo_intero()
        setattr(self, nome, valore)
        return valore


Qt = _QtFinto()


class _Segnale:
    def __init__(self, *args, **kwargs):
        self._slot = []

    def connect(self, slot):
        self._slot.append(slot)

    def disconnect(self, slot=None):
        self._slot = []

    def emit(self, *args, **kwargs):
        for s in list(self._slot):
            try:
                s(*args, **kwargs)
            except TypeError:
                s()


def pyqtSignal(*args, **kwargs):
    return _Segnale()


def pyqtSlot(*args, **kwargs):
    def _decoratore(fn):
        return fn
    return _decoratore


class QObject(_Qualsiasi):
    def __init__(self, parent=None):
        self._parent = parent

    def parent(self):
        return self._parent

    def objectName(self):
        return getattr(self, "_nome_oggetto", "")

    def setObjectName(self, nome):
        self._nome_oggetto = nome

    def deleteLater(self):
        pass


# ---------------------------------------------------------------------------
# qgis.core — campi, feature, layer, progetto


class _Null:
    """Sentinella dei valori nulli QGIS: falsa e uguale solo a se stessa."""

    def __repr__(self):
        return "NULL"

    def __eq__(self, altro):
        return isinstance(altro, _Null)

    def __ne__(self, altro):
        return not self.__eq__(altro)

    def __hash__(self):
        return hash("__TODO_NULL__")

    def __bool__(self):
        return False


NULL = _Null()


class FakeField:
    """Campo finto: name(), type() (QMetaType), typeName(), alias() come QGIS.

    Accetta `FakeField("nome", "stringa")` oppure la tupla `("nome", "stringa")`
    (cosi' gli schemi si scrivono come elenchi di tuple).
    """

    def __init__(self, nome, tipo="stringa", alias=None, lunghezza=0, precisione=0,
                 commento=""):
        if isinstance(nome, (tuple, list)):
            pezzi = list(nome)
            nome = pezzi[0]
            if len(pezzi) > 1 and tipo == "stringa":
                tipo = pezzi[1]
            if len(pezzi) > 2 and alias is None:
                alias = pezzi[2]
        elif isinstance(nome, dict):
            definizione = dict(nome)
            nome = definizione.pop("nome", definizione.pop("name", ""))
            tipo = definizione.pop("tipo", definizione.pop("type", tipo))
            alias = definizione.pop("alias", alias)
            lunghezza = definizione.pop("lunghezza", lunghezza)
            commento = definizione.pop("commento", commento)
        self._nome = str(nome)
        self._tipo, self._tipo_nome = _risolvi_tipo(tipo)
        self._alias = alias if alias is not None else str(nome)
        self._lunghezza = lunghezza
        self._precisione = precisione
        self._commento = commento

    def name(self):
        return self._nome

    def type(self):
        return self._tipo

    def typeName(self):
        return self._tipo_nome

    def alias(self):
        return self._alias

    def setAlias(self, alias):
        self._alias = alias

    def comment(self):
        return self._commento

    def setComment(self, commento):
        self._commento = commento

    def length(self):
        return self._lunghezza

    def precision(self):
        return self._precisione

    def isNumeric(self):
        return self._tipo in (
            QMetaType.Type.Int, QMetaType.Type.LongLong, QMetaType.Type.Double,
            QMetaType.Type.UInt, QMetaType.Type.ULongLong, QMetaType.Type.Float,
        )

    def __repr__(self):
        return "FakeField(%r, %r)" % (self._nome, self._tipo_nome)


_TIPI_FIELD = {
    "stringa": (QMetaType.Type.QString, "String"),
    "string": (QMetaType.Type.QString, "String"),
    "testo": (QMetaType.Type.QString, "String"),
    "guid": (QMetaType.Type.QString, "String"),
    "uuid": (QMetaType.Type.QString, "String"),
    "numerico": (QMetaType.Type.Double, "Real"),
    "double": (QMetaType.Type.Double, "Real"),
    "reale": (QMetaType.Type.Double, "Real"),
    "intero": (QMetaType.Type.Int, "Integer"),
    "int": (QMetaType.Type.Int, "Integer"),
    "long": (QMetaType.Type.LongLong, "Integer64"),
    "data": (QMetaType.Type.QDateTime, "DateTime"),
    "datetime": (QMetaType.Type.QDateTime, "DateTime"),
    "booleano": (QMetaType.Type.Bool, "Boolean"),
    "bool": (QMetaType.Type.Bool, "Boolean"),
    "blob": (QMetaType.Type.QByteArray, "Binary"),
    "binary": (QMetaType.Type.QByteArray, "Binary"),
}


def _risolvi_tipo(tipo):
    """'stringa' / QMetaType.Type.X -> (valore QMetaType, nome leggibile)."""
    if isinstance(tipo, str):
        chiave = tipo.strip().lower()
        if chiave in _TIPI_FIELD:
            return _TIPI_FIELD[chiave]
        return (QMetaType.Type.QString, "String")
    for valore, nome in set(_TIPI_FIELD.values()):
        if valore == tipo:
            return (valore, nome)
    return (tipo, "Another")


class FakeFields:
    """Collezione di campi: iterabile, indicizzabile per indice o per nome."""

    def __init__(self, campi=()):
        self._campi = [
            c if isinstance(c, FakeField) else FakeField(c) for c in campi
        ]

    def __len__(self):
        return len(self._campi)

    def __iter__(self):
        return iter(self._campi)

    def __getitem__(self, chiave):
        if isinstance(chiave, slice):
            return FakeFields(self._campi[chiave])
        if isinstance(chiave, int):
            return self._campi[chiave]
        for c in self._campi:
            if c.name() == chiave:
                return c
        raise KeyError(chiave)

    def __contains__(self, chiave):
        nome = chiave.name() if isinstance(chiave, FakeField) else chiave
        return any(c.name() == nome for c in self._campi)

    def names(self):
        return [c.name() for c in self._campi]

    def at(self, indice):
        return self._campi[indice]

    def indexFromName(self, nome):
        for i, c in enumerate(self._campi):
            if c.name() == nome:
                return i
        return -1

    def indexOf(self, nome):
        return self.indexFromName(nome)

    def exists(self, nome):
        return self.indexFromName(nome) >= 0

    def __repr__(self):
        return "FakeFields(%r)" % (self.names(),)


class FakeFeature:
    """Feature finta: campi + valori, con NULL di default e geometry opzionale."""

    def __init__(self, campi=None, valori=None, fid=None, geometria=None):
        self._campi = campi if isinstance(campi, FakeFields) else FakeFields()
        self._fid = fid
        self._valori = {}
        self._geometria = geometria
        self._valido = True
        if isinstance(valori, dict):
            for chiave, valore in valori.items():
                self[chiave] = valore

    # -- accesso stile QGIS -------------------------------------------------
    def _nome_da_chiave(self, chiave):
        if isinstance(chiave, FakeField):
            return chiave.name()
        if isinstance(chiave, int):
            return self._campi.at(chiave).name()
        return str(chiave)

    def __getitem__(self, chiave):
        nome = self._nome_da_chiave(chiave)
        if nome in self._valori:
            return self._valori[nome]
        if nome in self._campi:
            return NULL          # campo esistente ma non valorizzato -> NULL
        raise KeyError(nome)

    def __setitem__(self, chiave, valore):
        self._valori[self._nome_da_chiave(chiave)] = valore

    def __contains__(self, chiave):
        return self._nome_da_chiave(chiave) in self._valori

    def attribute(self, chiave):
        return self[chiave]

    def setAttribute(self, chiave, valore):
        self[chiave] = valore

    def attributes(self):
        return [self._valori.get(c.name(), NULL) for c in self._campi]

    def setAttributes(self, valori):
        self._valori = {}
        for i, valore in enumerate(valori):
            self[i] = valore

    # -- anagrafica ---------------------------------------------------------
    def id(self):
        return self._fid if self._fid is not None else -1

    def setId(self, fid):
        self._fid = fid

    def fields(self):
        return self._campi

    def setFields(self, campi):
        self._campi = campi

    def isValid(self):
        return self._valido

    def geometry(self):
        return self._geometria

    def setGeometry(self, geometria):
        self._geometria = geometria

    def hasGeometry(self):
        return self._geometria is not None

    def __repr__(self):
        return "FakeFeature(%r)" % (self._valori,)


class FakeGeometry:
    def __init__(self, wkt="POINT(0 0)"):
        self._wkt = wkt

    def asWkt(self, *args, **kwargs):
        return self._wkt

    def isEmpty(self):
        return not self._wkt

    def isNull(self):
        return not self._wkt

    def __repr__(self):
        return "FakeGeometry(%r)" % (self._wkt,)


class FakeProvider(_Qualsiasi):
    """Data provider finto: i metodi noti sono espliciti, gli altri no-op."""

    def __init__(self, layer):
        self._layer = layer

    def addFeatures(self, features, flags=0):
        for f in features:
            self._layer.addFeature(f)
        return (True, list(features))

    def deleteFeatures(self, fids):
        return bool(self._layer.deleteFeatures(fids))

    def fieldNameIndex(self, nome):
        return self._layer.fields().indexFromName(nome)

    def fields(self):
        return self._layer.fields()

    def featureCount(self):
        return self._layer.featureCount()

    def name(self):
        return self._layer.providerType()

    def supportsTransactions(self):
        return True


class FakeLayer:
    """Layer vettoriale finto con campi, feature e ciclo di editing.

    I metodi QGIS noti sono implementati; gli altri diventano no-op registrati in
    `chiamate_sconosciute` (utile per capire cosa il plugin si aspetta da QGIS).
    """

    VectorLayer = 0
    RasterLayer = 1
    PluginLayer = 2
    MeshLayer = 3
    VectorTileLayer = 4
    AnnotationLayer = 5
    PointCloudLayer = 6
    GroupLayer = 7

    # Sorgenti registrate: source -> (campi, feature). Vedi `registra_sorgente`.
    registro_sorgenti = {}

    def __init__(self, source="", nome="", provider="ogr", campi=None, feature=None):
        self._source = source or ""
        self._nome = nome or ""
        self._provider = provider or "ogr"
        self._valid = True
        self._editing = False
        self._features = []
        self.chiamate_sconosciute = []
        self._provider_finto = FakeProvider(self)

        registrati = self.registro_sorgenti.get(self._source)
        if registrati:
            campi = campi if campi is not None else registrati[0]
            feature = feature if feature is not None else registrati[1]
        self._fields = campi if isinstance(campi, FakeFields) else FakeFields(campi or [])
        for f in (feature or []):
            self.addFeature(f)

    # -- anagrafica ---------------------------------------------------------
    def name(self):
        return self._nome

    def setName(self, nome):
        self._nome = nome

    def id(self):
        return self._nome or self._source

    def source(self):
        return self._source

    def providerType(self):
        return self._provider

    def type(self):
        return FakeLayer.VectorLayer

    def isValid(self):
        return self._valid

    def setValid(self, valido):
        self._valid = valido

    # -- campi --------------------------------------------------------------
    def fields(self):
        return self._fields

    def setFields(self, campi):
        self._fields = campi if isinstance(campi, FakeFields) else FakeFields(campi)

    # -- feature ------------------------------------------------------------
    def featureCount(self):
        return len(self._features)

    def getFeatures(self, request=None):
        features = list(self._features)
        if request is not None:
            fids = getattr(request, "fids", None) or getattr(request, "_fids", None)
            if fids:
                features = [f for f in features if f.id() in set(fids)]
        return iter(features)

    def addFeature(self, feature, makeGeometry=True):
        if not isinstance(feature, FakeFeature):
            return False
        if feature.id() is None or feature.id() < 0:
            feature.setId((max([f.id() for f in self._features], default=0) + 1))
        self._features.append(feature)
        return True

    def updateFeature(self, feature, *args, **kwargs):
        for i, esistente in enumerate(self._features):
            if esistente.id() == feature.id():
                self._features[i] = feature
                return True
        return False

    def deleteFeature(self, fid):
        prima = len(self._features)
        self._features = [f for f in self._features if str(f.id()) != str(fid)]
        return len(self._features) != prima

    def deleteFeatures(self, fids):
        esito = False
        for fid in fids:
            esito = self.deleteFeature(fid) or esito
        return esito

    def selectedFeatures(self):
        return iter([])

    def selectAll(self):
        return True

    def selectedFeatureCount(self):
        return 0

    # -- editing ------------------------------------------------------------
    def startEditing(self):
        self._editing = True
        return True

    def isEditable(self):
        return self._editing

    def commitChanges(self):
        self._editing = False
        return True

    def rollback(self):
        self._editing = False
        return True

    def dataProvider(self):
        return self._provider_finto

    # -- stile / contorno ---------------------------------------------------
    def loadNamedStyle(self, percorso, *args, **kwargs):
        if not os.path.exists(percorso):
            return ("File di stile non trovato: %s" % percorso, False)
        self.stile_caricato = percorso
        return ("Stile caricato", True)

    def saveNamedStyle(self, percorso, *args, **kwargs):
        self.stile_salvato = percorso
        return ("Stile salvato", True)

    def setSubsetString(self, filtro):
        self._subset = filtro

    def subsetString(self):
        return getattr(self, "_subset", "")

    def extent(self):
        return _Qualsiasi()

    def wkbType(self):
        return 1

    def geometryType(self):
        return "Point"

    def crs(self):
        return _Qualsiasi()

    def setCrs(self, crs):
        pass

    def updateExtents(self):
        pass

    def triggerRepaint(self):
        pass

    def __getattr__(self, nome):
        if nome.startswith("__"):
            raise AttributeError(nome)

        def _registra(*args, **kwargs):
            self.chiamate_sconosciute.append((nome, args, kwargs))
            return None
        _registra.__name__ = nome
        return _registra

    def __repr__(self):
        return "FakeLayer(%r, %d feature, campi=%r)" % (
            self._nome, len(self._features), self._fields.names())


class QgsMapLayerType(_EnumAuto):
    VectorLayer = 0
    RasterLayer = 1
    PluginLayer = 2
    MeshLayer = 3
    VectorTileLayer = 4


class QgsWkbTypes(_EnumAuto):
    Unknown = 0
    Point = 1
    LineString = 2
    Polygon = 3


class Qgis(_Qualsiasi):
    class LayerType(_EnumAuto):
        Vector = 0
        Raster = 1
        Mesh = 3
        VectorTile = 4

    class GeometryType(_EnumAuto):
        Point = 0
        Line = 1
        Polygon = 2


class FakeLayerTree(_Qualsiasi):
    def __init__(self, progetto):
        self._progetto = progetto

    def findLayer(self, layer_id):
        return None


class FakeProject:
    """Progetto finto: registro di layer, `instance()` singleton come QGIS."""

    _istanza = None

    def __init__(self):
        self._layer = {}          # id -> layer
        self.ordine = []
        self.chiamate_sconosciute = []

    @classmethod
    def instance(cls):
        if cls._istanza is None:
            cls._istanza = cls()
        return cls._istanza

    @classmethod
    def _azzera(cls):
        cls._istanza = cls()
        return cls._istanza

    # -- API progettuale ----------------------------------------------------
    def addMapLayer(self, layer, addToLegend=True):
        layer_id = layer.id()
        self._layer[layer_id] = layer
        if layer_id not in self.ordine:
            self.ordine.append(layer_id)
        return layer

    def mapLayers(self):
        return dict(self._layer)

    def mapLayersByName(self, nome):
        return [lyr for lyr in self._layer.values() if lyr.name() == nome]

    def removeMapLayer(self, chiave):
        layer_id = chiave.id() if hasattr(chiave, "id") else chiave
        self._layer.pop(layer_id, None)
        if layer_id in self.ordine:
            self.ordine.remove(layer_id)

    def removeAllMapLayers(self):
        self._layer.clear()
        self.ordine.clear()

    def layerTreeRoot(self):
        return FakeLayerTree(self)

    def layersByName(self, nome):
        return self.mapLayersByName(nome)

    def __getattr__(self, nome):
        if nome.startswith("__"):
            raise AttributeError(nome)

        def _registra(*args, **kwargs):
            self.chiamate_sconosciute.append((nome, args, kwargs))
            return None
        _registra.__name__ = nome
        return _registra


class QgsApplication(_Qualsiasi):
    def __init__(self, *args, **kwargs):
        self._attivo = False

    @classmethod
    def setPrefixPath(cls, *args, **kwargs):
        return None

    @classmethod
    def initQgis(cls):
        return None

    @classmethod
    def exitQgis(cls):
        return None

    @classmethod
    def instance(cls):
        return cls()

    @classmethod
    def applicationDirPath(cls):
        return "/tmp/finto-qgis"


class FakeFeatureRequest:
    def __init__(self, *args, **kwargs):
        self.fids = []
        self.expression = None
        self.subset_of_attributes = None

    def setFilterFids(self, fids):
        self.fids = list(fids)


@contextmanager
def edit(layer):
    """Contesto `with edit(layer)`: commit in uscita, rollback se solleva."""
    istantanea = list(getattr(layer, "_features", []))
    layer.startEditing()
    try:
        yield
    except BaseException:
        try:
            layer._features = istantanea
        except AttributeError:
            pass
        layer.rollback()
        raise
    else:
        layer.commitChanges()


# ---------------------------------------------------------------------------
# qgis.gui / qgis.utils


class QgsMapTool(QObject):
    def __init__(self, canvas=None, *args, **kwargs):
        super().__init__()
        self.canvas = canvas
        self.cursore = None

    def activate(self):
        self.attivo = True

    def deactivate(self):
        self.attivo = False

    def setCursor(self, cursore):
        self.cursore = cursore

    def canvasReleaseEvent(self, evento):     # pragma: no cover - override nei test
        pass


class QgsMapToolIdentify(QgsMapTool):
    TopDownStopAtFirst = 0
    TopDownAll = 1
    LayerSelection = 0
    ActiveLayer = 1

    def identify(self, *args, **kwargs):
        return []


class QgsMapCanvas(_Qualsiasi):
    def __init__(self, *args, **kwargs):
        self._tool = None
        self.rifreschi = 0

    def setMapTool(self, tool):
        self._tool = tool

    def mapTool(self):
        return self._tool

    def refresh(self):
        self.rifreschi += 1


class FakeIface(_Qualsiasi):
    """`iface` finta da console QGIS: canvas, form, messaggi."""

    def __init__(self):
        self._canvas = QgsMapCanvas()
        self._active = None
        self.form_aperti = []
        self.messaggi = []

    def mapCanvas(self):
        return self._canvas

    def activeLayer(self):
        return self._active

    def setActiveLayer(self, layer):
        self._active = layer

    def openFeatureForm(self, layer, feature, updateFeature=False):
        self.form_aperti.append((layer, feature, updateFeature))

    def messageBar(self):
        return _Qualsiasi()

    def statusBar(self):
        return _Qualsiasi()


# ---------------------------------------------------------------------------
# qgis.PyQt.QtWidgets — dialoghi che registrano cosa e' stato chiesto


REGISTRO_DIALOGHI = []


class _Risposte:
    """Risposte preimpostabili per i dialoghi finti (code FIFO).

    Esempio:
        risposte.item.append(("fotorilievo__ATTACH", True))
        risposte.directory.append("/tmp/foto")
    """

    def __init__(self):
        self.item = []
        self.testo = []
        self.directory = []
        self.file = []
        self.si_no = []

    def svuota(self):
        for coda in (self.item, self.testo, self.directory, self.file, self.si_no):
            del coda[:]


risposte = _Risposte()


class QMessageBox(_Qualsiasi):
    Information = 1
    Warning = 2
    Critical = 3
    Question = 4
    Yes = 16384
    No = 65536
    Ok = 1024
    Cancel = 4194304
    StandardButton = _EnumAuto

    def __init__(self, parent=None, *args, **kwargs):
        self.parent = parent
        self.testo = ""
        self.titolo = ""
        self.informativo = ""
        self.bottoni = []

    def setText(self, testo):
        self.testo = testo

    def setInformativeText(self, testo):
        self.informativo = testo

    def setWindowTitle(self, titolo):
        self.titolo = titolo

    def addButton(self, *args, **kwargs):
        self.bottoni.append(args)
        return args[0] if args else None

    def setStandardButtons(self, *args):
        pass

    def button(self, *args, **kwargs):
        return None

    def exec_(self):
        return risposte.si_no.pop(0) if risposte.si_no else QMessageBox.Ok

    exec = exec_

    # -- statiche -----------------------------------------------------------
    @staticmethod
    def _registra(livello, parent, titolo, testo, *args, **kwargs):
        REGISTRO_DIALOGHI.append({
            "tipo": livello, "titolo": titolo, "testo": testo, "parent": parent,
        })
        return QMessageBox.Ok

    @staticmethod
    def information(parent, titolo, testo, *args, **kwargs):
        return QMessageBox._registra("information", parent, titolo, testo)

    @staticmethod
    def warning(parent, titolo, testo, *args, **kwargs):
        return QMessageBox._registra("warning", parent, titolo, testo)

    @staticmethod
    def critical(parent, titolo, testo, *args, **kwargs):
        return QMessageBox._registra("critical", parent, titolo, testo)

    @staticmethod
    def question(parent, titolo, testo, *args, **kwargs):
        QMessageBox._registra("question", parent, titolo, testo)
        return risposte.si_no.pop(0) if risposte.si_no else QMessageBox.Yes


class QInputDialog(_Qualsiasi):
    @staticmethod
    def getItem(parent, titolo, etichetta, voci, corrente=0, modificabile=False):
        REGISTRO_DIALOGHI.append({
            "tipo": "getItem", "titolo": titolo, "etichetta": etichetta,
            "voci": list(voci), "corrente": corrente,
        })
        if risposte.item:
            return risposte.item.pop(0)
        if voci:
            return (voci[corrente if 0 <= corrente < len(voci) else 0], True)
        return ("", False)

    @staticmethod
    def getText(parent, titolo, etichetta, *args, **kwargs):
        if risposte.testo:
            return risposte.testo.pop(0)
        return ("", False)

    @staticmethod
    def getInt(parent, titolo, etichetta, valore=0, minimo=0, massimo=100, passo=1):
        return (valore, False)

    @staticmethod
    def getDouble(parent, titolo, etichetta, valore=0.0, *args, **kwargs):
        return (valore, False)


class QFileDialog(_Qualsiasi):
    @staticmethod
    def getExistingDirectory(parent, titolo, cartella="", *args, **kwargs):
        REGISTRO_DIALOGHI.append({"tipo": "getExistingDirectory", "titolo": titolo})
        return risposte.directory.pop(0) if risposte.directory else ""

    @staticmethod
    def getOpenFileName(parent, titolo, cartella="", *args, **kwargs):
        REGISTRO_DIALOGHI.append({"tipo": "getOpenFileName", "titolo": titolo})
        return risposte.file.pop(0) if risposte.file else ("", "")

    @staticmethod
    def getSaveFileName(parent, titolo, cartella="", *args, **kwargs):
        REGISTRO_DIALOGHI.append({"tipo": "getSaveFileName", "titolo": titolo})
        return risposte.file.pop(0) if risposte.file else ("", "")


# ---------------------------------------------------------------------------
# Costruzione e iniezione dei moduli


def _modulo(nome, attributi=None, package=True):
    modulo = types.ModuleType(nome)
    if package:
        modulo.__path__ = []
    cache = {}

    def _getattr(name, _cache=cache):
        if name.startswith("__"):
            raise AttributeError(name)
        if name not in _cache:
            _cache[name] = _crea_stub(name)
        return _cache[name]

    modulo.__getattr__ = _getattr
    if attributi:
        modulo.__dict__.update(attributi)
    sys.modules[nome] = modulo
    return modulo


_INSTALLATO = False


def install(force=False):
    """Inietta i moduli finti in sys.modules. Idempotente."""
    global _INSTALLATO
    if _INSTALLATO and not force:
        return sys.modules["qgis"]
    _INSTALLATO = True

    # -- QtCore -------------------------------------------------------------
    qtcore = _modulo("qgis.PyQt.QtCore", {
        "QByteArray": QByteArray,
        "QVariant": QVariant,
        "QMetaType": QMetaType,
        "Qt": Qt,
        "QObject": QObject,
        "pyqtSignal": pyqtSignal,
        "pyqtSlot": pyqtSlot,
        "QDateTime": _crea_stub("QDateTime"),
        "QDate": _crea_stub("QDate"),
        "QTime": _crea_stub("QTime"),
        "QTimer": _crea_stub("QTimer"),
        "QSize": _crea_stub("QSize"),
        "QSizeF": _crea_stub("QSizeF"),
        "QRect": _crea_stub("QRect"),
        "QPoint": _crea_stub("QPoint"),
        "QPointF": _crea_stub("QPointF"),
        "QUrl": _crea_stub("QUrl"),
        "QSettings": _crea_stub("QSettings"),
        "QRegularExpression": _crea_stub("QRegularExpression"),
        "QStringList": list,
        "QThread": _crea_stub("QThread"),
        "QSortFilterProxyModel": _crea_stub("QSortFilterProxyModel"),
        "QAbstractTableModel": _crea_stub("QAbstractTableModel"),
        "NULL": NULL,
        "__fake_qgis__": True,
    })

    qtgui = _modulo("qgis.PyQt.QtGui", {
        "QCursor": _crea_stub("QCursor"),
        "QIcon": _crea_stub("QIcon"),
        "QColor": _crea_stub("QColor"),
        "QFont": _crea_stub("QFont"),
        "QPixmap": _crea_stub("QPixmap"),
        "QPainter": _crea_stub("QPainter"),
        "QBrush": _crea_stub("QBrush"),
        "QPen": _crea_stub("QPen"),
        "QAction": _crea_stub("QAction"),
        "QKeySequence": _crea_stub("QKeySequence"),
    })

    qt_widgets = {
        "QMessageBox": QMessageBox,
        "QInputDialog": QInputDialog,
        "QFileDialog": QFileDialog,
        "QDialog": _crea_stub("QDialog"),
        "QWizard": _crea_stub("QWizard"),
        "QWizardPage": _crea_stub("QWizardPage"),
        "QWidget": _crea_stub("QWidget"),
        "QLabel": _crea_stub("QLabel"),
        "QLineEdit": _crea_stub("QLineEdit"),
        "QPlainTextEdit": _crea_stub("QPlainTextEdit"),
        "QTextEdit": _crea_stub("QTextEdit"),
        "QPushButton": _crea_stub("QPushButton"),
        "QToolButton": _crea_stub("QToolButton"),
        "QCheckBox": _crea_stub("QCheckBox"),
        "QComboBox": _crea_stub("QComboBox"),
        "QRadioButton": _crea_stub("QRadioButton"),
        "QSpinBox": _crea_stub("QSpinBox"),
        "QDoubleSpinBox": _crea_stub("QDoubleSpinBox"),
        "QGroupBox": _crea_stub("QGroupBox"),
        "QListView": _crea_stub("QListView"),
        "QListWidget": _crea_stub("QListWidget"),
        "QListWidgetItem": _crea_stub("QListWidgetItem"),
        "QTableWidget": _crea_stub("QTableWidget"),
        "QTableWidgetItem": _crea_stub("QTableWidgetItem"),
        "QProgressDialog": _crea_stub("QProgressDialog"),
        "QProgressBar": _crea_stub("QProgressBar"),
        "QApplication": _crea_stub("QApplication"),
        "QDialogButtonBox": _crea_stub("QDialogButtonBox"),
        "QVBoxLayout": _crea_stub("QVBoxLayout"),
        "QHBoxLayout": _crea_stub("QHBoxLayout"),
        "QFormLayout": _crea_stub("QFormLayout"),
        "QGridLayout": _crea_stub("QGridLayout"),
        "QStackedWidget": _crea_stub("QStackedWidget"),
        "QTabWidget": _crea_stub("QTabWidget"),
        "QScrollArea": _crea_stub("QScrollArea"),
        "QMenu": _crea_stub("QMenu"),
        "QAction": _crea_stub("QAction"),
        "QFileSystemModel": _crea_stub("QFileSystemModel"),
        "QAbstractItemView": _EnumAuto,
        "QSizePolicy": _EnumAuto,
        "QDialogButtonBox_StandardButton": _EnumAuto,
    }
    qtwidgets = _modulo("qgis.PyQt.QtWidgets", qt_widgets)

    # `qgis.PyQt.Qt` non e' un modulo Qt vero: esiste in alcune versioni QGIS.
    qt_onnivoro = _modulo("qgis.PyQt.Qt", dict(qtcore.__dict__))

    qtnetwork = _modulo("qgis.PyQt.QtNetwork")
    qtxml = _modulo("qgis.PyQt.QtXml")
    qtsql = _modulo("qgis.PyQt.QtSql")
    qtsvg = _modulo("qgis.PyQt.QtSvg")
    qtsupport = _modulo("qgis.PyQt.QtPrintSupport")
    qtqml = _modulo("qgis.PyQt.QtQml")

    pyqt = _modulo("qgis.PyQt", {
        "QtCore": qtcore, "QtGui": qtgui, "QtWidgets": qtwidgets, "Qt": qt_onnivoro,
        "QtNetwork": qtnetwork, "QtXml": qtxml, "QtSql": qtsql, "QtSvg": qtsvg,
        "QtPrintSupport": qtsupport, "QtQml": qtqml,
        "sip": _crea_stub("sip"),
    })

    # -- qgis.core ----------------------------------------------------------
    core = _modulo("qgis.core", {
        "QgsVectorLayer": FakeLayer,
        "QgsMapLayer": FakeLayer,
        "QgsFeature": FakeFeature,
        "QgsField": FakeField,
        "QgsFields": FakeFields,
        "QgsProject": FakeProject,
        "QgsGeometry": FakeGeometry,
        "QgsPointXY": _crea_stub("QgsPointXY"),
        "QgsRectangle": _crea_stub("QgsRectangle"),
        "QgsFeatureRequest": FakeFeatureRequest,
        "QgsFeatureIterator": _crea_stub("QgsFeatureIterator"),
        "QgsExpression": _crea_stub("QgsExpression"),
        "QgsExpressionContext": _crea_stub("QgsExpressionContext"),
        "QgsApplication": QgsApplication,
        "QgsMapLayerType": QgsMapLayerType,
        "QgsWkbTypes": QgsWkbTypes,
        "Qgis": Qgis,
        "QgsCoordinateReferenceSystem": _crea_stub("QgsCoordinateReferenceSystem"),
        "QgsVectorDataProvider": FakeProvider,
        "QgsDistanceArea": _crea_stub("QgsDistanceArea"),
        "QgsMessageLog": _crea_stub("QgsMessageLog"),
        "QgsSettings": _crea_stub("QgsSettings"),
        "QgsUnitTypes": _EnumAuto,
        "QgsFieldConstraints": _EnumAuto,
        "QgsVectorFileWriter": _crea_stub("QgsVectorFileWriter"),
        "QgsFeatureSink": _EnumAuto,
        "QgsSpatialIndex": _crea_stub("QgsSpatialIndex"),
        "QgsRendererCategory": _crea_stub("QgsRendererCategory"),
        "QgsCategorizedSymbolRenderer": _crea_stub("QgsCategorizedSymbolRenderer"),
        "QgsSingleSymbolRenderer": _crea_stub("QgsSingleSymbolRenderer"),
        "QgsSymbol": _crea_stub("QgsSymbol"),
        "QgsMarkerSymbol": _crea_stub("QgsMarkerSymbol"),
        "QgsFillSymbol": _crea_stub("QgsFillSymbol"),
        "QgsLineSymbol": _crea_stub("QgsLineSymbol"),
        "QgsTask": _crea_stub("QgsTask"),
        "NULL": NULL,
        "edit": edit,
        "QgsMapLayerTypes": QgsMapLayerType,
        "QgsFeatureSource": _EnumAuto,
        "__fake_qgis__": True,
    })

    gui = _modulo("qgis.gui", {
        "QgsMapTool": QgsMapTool,
        "QgsMapToolIdentify": QgsMapToolIdentify,
        "QgsMapCanvas": QgsMapCanvas,
        "QgsMapToolEmitPoint": _crea_stub("QgsMapToolEmitPoint"),
        "QgsMapToolPan": _crea_stub("QgsMapToolPan"),
        "QgsRubberBand": _crea_stub("QgsRubberBand"),
        "QgsHighlight": _crea_stub("QgsHighlight"),
        "QgsGui": _crea_stub("QgsGui"),
        "QgsAttributeForm": _crea_stub("QgsAttributeForm"),
        "QgsAttributeEditorContext": _crea_stub("QgsAttributeEditorContext"),
        "QgsMapLayerComboBox": _crea_stub("QgsMapLayerComboBox"),
        "QgsMessageBar": _crea_stub("QgsMessageBar"),
        "QgsDialog": _crea_stub("QgsDialog"),
        "__fake_qgis__": True,
    })

    utils = _modulo("qgis.utils", {
        "iface": FakeIface(),
        "plugins": {},
        "startEditing": _finto_callable("startEditing"),
        "QGIS_VERSION": "3.fake",
        "__fake_qgis__": True,
    })

    qgis = _modulo("qgis", {
        "core": core, "gui": gui, "utils": utils, "PyQt": pyqt,
        "__version__": "3.fake",
        "__fake_qgis__": True,
    })
    return qgis


def disinstalla():
    """Rimuove i moduli finti (per test che vogliono verificare l'assenza)."""
    global _INSTALLATO
    for nome in [n for n in list(sys.modules) if n == "qgis" or n.startswith("qgis.")]:
        del sys.modules[nome]
    _INSTALLATO = False


def azzera_tutto():
    """Riporta allo stato iniziale progetto, dialoghi e code di risposte.

    Richiamata dalle fixture autouse di conftest.py prima e dopo ogni test.
    """
    FakeProject._azzera()
    FakeLayer.registro_sorgenti.clear()
    del REGISTRO_DIALOGHI[:]
    risposte.svuota()


# ---------------------------------------------------------------------------
# Aiutanti per costruire dati di prova


#: Campi tipici di un layer sorgente su FileGDB (nome + tipo del campo).
SCHEMA_SORGENTE = (
    ("GLOBALID", "stringa"),
    ("Nome", "stringa"),
    ("filefoto", "stringa"),
    ("FOTO_EST", "stringa"),
)

#: I 6 campi della tabella allegati (schema del ticket 02).
SCHEMA_ATTACH = (
    ("GLOBALID", "stringa"),
    ("REL_GLOBALID", "stringa"),
    ("CONTENT_TYPE", "stringa"),
    ("DATA_SIZE", "intero"),
    ("ATT_NAME", "stringa"),
    ("DATA", "blob"),
)

#: GUID finti riusabili (maiuscoli, senza graffe come li scrive il plugin).
GUID_1 = "0F1E2D3C-4B5A-6978-8796-A5B4C3D2E1F0"
GUID_2 = "1A2B3C4D-5E6F-7081-92A3-B4C5D6E7F809"
GUID_3 = "AA11BB22-CC33-DD44-EE55-FF6677889900"


def crea_feature(campi=None, valori=None, fid=None):
    """Feature finta a partire da un dizionario {campo: valore}."""
    return FakeFeature(campi=FakeFields(campi or []), valori=valori, fid=fid)


def registra_sorgente(source, campi=None, feature=None):
    """Registra campi/feature per una `source`, cosi' QgsVectorLayer(source,...)

    li adotta (utile per simulare un </percorso.gdb|layername=...> caricato).
    """
    FakeLayer.registro_sorgenti[source] = (
        FakeFields(campi or []), list(feature or []))


def crea_layer_sorgente(nome="fotorilievo", campi=None, feature=None, source=None,
                        provider="ogr"):
    """Layer sorgente finto: GLOBALID + campo foto, con feature plausibili."""
    campi = campi if campi is not None else SCHEMA_SORGENTE
    if feature is None:
        feature = [
            crea_feature(campi, {"GLOBALID": GUID_1, "Nome": "pozzetto 1",
                                 "filefoto": "SS_0001.jpg", "FOTO_EST": "SS_0001"}),
            crea_feature(campi, {"GLOBALID": GUID_2, "Nome": "pozzetto 2",
                                 "filefoto": "", "FOTO_EST": NULL}),
        ]
    return FakeLayer(source=source or "", nome=nome, provider=provider,
                     campi=campi, feature=feature)


def crea_layer_attach(nome="fotorilievo__ATTACH", allegati=None, campi=None,
                      source=None):
    """Tabella allegati finta (schema a 6 campi), vuota o con righe date.

    `allegati` e' una lista di dizionari {GLOBALID, REL_GLOBALID, CONTENT_TYPE,
    DATA_SIZE, ATT_NAME, DATA}.
    """
    campi = campi if campi is not None else SCHEMA_ATTACH
    layer = FakeLayer(source=source or "", nome=nome, campi=campi)
    for i, riga in enumerate(allegati or [], start=1):
        valore = {"GLOBALID": riga.get("GLOBALID", "AABBCCDD-0000-1111-2222-334455667788"),
                  "CONTENT_TYPE": riga.get("CONTENT_TYPE", "image/jpeg"),
                  "DATA": riga.get("DATA", b"\x89PNG..."),
                  "ATT_NAME": riga.get("ATT_NAME", "")}
        valore["REL_GLOBALID"] = riga.get("REL_GLOBALID", "{%s}" % GUID_1)
        valore["DATA_SIZE"] = riga.get("DATA_SIZE", len(valore["DATA"]))
        layer.addFeature(FakeFeature(campi=FakeFields(campi), valori=valore, fid=i))
    return layer


def carica(percorso, nome_modulo=None):
    """Importa un file .py per percorso (il plugin non e' un pacchetto installato).

    Esempio: carica("gdb_attacher/naming.py")
    """
    percorso = os.path.abspath(str(percorso))
    if nome_modulo is None:
        nome_modulo = "modulo_prova_" + os.path.splitext(os.path.basename(percorso))[0]
    spec = importlib.util.spec_from_file_location(nome_modulo, percorso)
    if spec is None or spec.loader is None:
        raise ImportError("non riesco a importare %s" % percorso)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome_modulo] = modulo
    spec.loader.exec_module(modulo)
    return modulo
