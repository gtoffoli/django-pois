# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.utils.encoding import python_2_unicode_compatible

import datetime
from collections import defaultdict
# from lxml.html.clean import clean_html, fromstring
import feedparser

# Add before admin.autodiscover() and any form import for that matter:
# MMR import autocomplete_light
# MMR autocomplete_light.autodiscover()

from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
# from django.template.defaultfilters import slugify
# from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _ # , string_concat
from django.contrib.gis.db import models as geomodels
from django.contrib.gis.geos import Point, MultiPolygon, LineString, MultiLineString
from django.contrib.gis.measure import D # ``D`` is a shortcut for ``Distance
# MMR old version - from django.contrib.contenttypes import generic
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
# MMR from richtext_blog.models import Post
from autoslug import AutoSlugField
# from autoslug.settings import slugify as default_slugify
from datatrans.utils import register
from datatrans.models import KeyValue

from django.conf import settings
POITYPE_SLUGS = settings.POITYPE_SLUGS

srid_GPS = 4326 # WGS84 = World Geodetic System 1984 (the reference system used by GPS)
# srid_OSM = 900913 # the Google Map's modified Mercator projection (default in PostGIS, used by OSM)
srid_OSM = 3857 # the projection used by OSM, GMaps and Bing tile server
srid_ISTAT = 23032
# from pois.views import roma_lon, roma_lat
roma_lon = 12.4750
roma_lat = 41.9050

STATE_CHOICES = (
    (0, 'new'),
    (1, 'ok'),
    (2, 'off'),)

"""
poi_icon_map = {
    '03170248': ('museum', 'Green'), # Museums and art galleries
    '0425': ('theatre', 'Red'), # 
    '05280364': ('greencross', 'Green'), # chemists
    '05280365': ('hospital', 'Green'), # clinic  
    '05280367': ('ampoule', 'Green'), # medical laboratory
    '05280371': ('hospital', 'Red'), # hospital
    '05280815': ('daycenter', 'Red'), # Ambulatori    
    '0528': ('redcross', 'Red'), # medical ..
    '0530': ('coop', 'Blue'),
    '05310375': ('childcare', 'Blue'), # First, primary and infant school
    '0531': ('school', 'Black'),
    '06330414': ('redstar', 'Red'), # Fire brigade stations
    '06330422': ('bluestar', 'Blue'), # Police stations
    '06330416': ('pal', 'Black'), # Local government
    '06330426': ('pal', 'Black'), # Registrar's offices
    '06340458': ('library', 'Green'),
    '0634045910': ('church', 'BlueViolet'), # parrocchie cattoliche
    '0635045210': ('fleurdelis', 'BlueViolet'), # Associazione scout
    '0635076911': ('citizencommittee', 'Red'), # Comitato di quartieer
    '063507691': ('neigborhood', 'Red'), # Associazione di quartiere
    '0635076921': ('seniorscentre', 'Red'), # Social centre for older/elderly people
    '0635076922': ('socialcentre', 'Red'), # Self managed social centre
    '0635081610': ('ear', 'Red'), # Centro di ascolto
    '0635081620': ('soupcup', 'Red'), # Mensa
    '06350817': ('leaf', 'Green'), # Conservation organizationa
    '09480763': ('post', 'Black'), # Post offices
    '09480674': ('bookshop', 'Green'), # Books and maps
    '09480689': ('music', 'Blue'), # Music and video
    '09480712': ('antiques', 'FireBrick'), # Music and video
}
"""
poi_icon_map = {}

poi_klass_prefixes = {
    '05280364': ('Farmacia', ('farmaci')), # chemists
    '05301100': ('Coop. sociale', ('coop',)),
    '05301110': ('Coop. sociale', ('coop',)),
    '05301120': ('Coop. sociale', ('coop',)),
    '05301130': ('Coop. sociale', ('coop',)),
    '05301140': ('Coop. sociale', ('coop',)),
    '05301150': ('Consorzio', ('cons',)),
    '0531037510': ('Asilo nido', ('asilo', 'nido',)),
    '0531037520': ('Scuola materna', ('scuola', 'materna', 'infanzia',)), # 
    '053103792':  ('IIS', ('iis', 'liceo', 'istituto',)),
    '0531037921': ('Liceo', ('liceo',)),
    "0531037922": ('Istituto Professionale', ('ip', 'istituto',)),
    "0531037923": ('Istituto Tecnico', ('it', 'istituto',)),
    '0634045910': ('Parrocchia', ('parrocchia', 'chiesa',)),
}

MACROZONE = 0
TOPOZONE = 3
CAPZONE = 6
MUNICIPIO = 7

zone_prefix_dict = {
    'R': ('rione', _('historical quarter'), _('historical quarters')),
    'Q': ('quartiere', _('quarter'), _('quarters')),
    'S': ('suburbio', _('quarter extension'), _('quarter extensions')),
    'Z': ('zona', _('suburban zone'), _('suburban zones')),
    'M': ('municipio', _('municipality'), _('municipalities')),
    'C': ('comune', _('town'), _('towns')),
    '0': ('cap', _('zipcode'), _('zipcode areas')),
}

def rebuild_icon_map():
    global poi_icon_map
    poi_icon_map = {}
    poitypes = Poitype.objects.exclude(icon__isnull=True).exclude(icon='').order_by('-klass')
    for pt in poitypes:
        klass = pt.klass
        if len(klass)==8 and klass[4:]=='0000':
            klass = klass[:4]
        poi_icon_map[klass] = (pt.icon, pt.color)
    
poi_categories = []

def rebuild_poi_categories():
    global poi_categories
    poi_categories = []
    poitypes = Poitype.objects.filter(active=True)
    for pt in poitypes:
        klass = pt.klass
        if len(klass)==8 and klass[4:]=='0000':
            poi_categories.append(klass)

def get_language(instance):
    return instance.request.LANGUAGE_CODE

# https://docs.djangoproject.com/en/dev/ref/models/fields/
## http://www.eivanov.com/2009/01/manytomany-relations-in-django.html
# http://stackoverflow.com/questions/4907913/how-do-i-tell-django-to-not-create-a-table-for-an-m2m-related-field
class ManyToManyField_NoSyncdb(models.ManyToManyField):
    def __init__(self, *args, **kwargs):
        super(ManyToManyField_NoSyncdb, self).__init__(*args, **kwargs)
        self.creates_table = False

# Create your models here.

class Sourcetype(models.Model):
    name = models.CharField(max_length=40)

    class Meta:
        verbose_name = "tipo di fonte"
        verbose_name_plural = "tipi di fonte"

    def __str__(self):
        return self.name

@python_2_unicode_compatible
class Zonetype(models.Model):
    # name = models.CharField(max_length=20)
    name_en = models.CharField(max_length=40, blank=True)
    # name_it = models.CharField(max_length=40)
    name = models.CharField(max_length=40)
    name_plural_en = models.CharField(max_length=40, blank=True)
    # name_plural_it = models.CharField(max_length=40, blank=True)
    name_plural = models.CharField(max_length=40, blank=True)
    # slug = AutoSlugField(unique=True, populate_from='name_it', editable=True)
    slug = AutoSlugField(unique=True, populate_from='name', editable=True)

    class Meta:
        verbose_name = "tipo di zona"
        verbose_name_plural = "tipi di zona"

    def getName(self, language='it'):
        """
        name = language.startswith('it') and self.name_it or self.name_en
        return name
        """
        return self.name

    def getNamePlural(self, language='it'):
        """
        name = language.startswith('it') and self.name_plural_it or self.name_plural_en
        return name
        """
        return self.name_plural

    def __str__(self):
        # return self.getName(language='it')
        return self.name
    
    def list_topo_zones(self):
        """ return all zones of this type as a list of items (type, sublist) """
        # zones = Zone.objects.filter(zonetype_id=self.id)
        # zones = Zone.objects.filter(zonetype_id=self.id).values('id', 'code', 'name', 'slug')
        zones = Zone.objects.filter(zonetype_id=self.id).exclude(geom__isnull=True).values('id', 'code', 'name', 'slug').order_by('name')
        return split_topo_zones(zones)  

def reordered_zonetype(zonetype):
    if zonetype==1:
        return 2
    elif zonetype==7:
        return 1
    else:
        return zonetype

@python_2_unicode_compatible
class Zone(geomodels.Model):
    # id = models.AutoField(primary_key=True)
    # campi originali
    code = models.CharField('Codice', max_length=10)
    name = models.CharField('Nome', max_length=50)
    zonetype = models.ForeignKey(Zonetype, models.PROTECT, blank=True, null=True)
    pro_com = models.IntegerField('Comune', blank=True, null=True, default=58091)
    slug = AutoSlugField(unique=True, populate_from='name', editable=True)
    short = models.CharField(verbose_name='Toponimi', max_length=200, null=True, blank=True)
    description = models.TextField(verbose_name='Descrizione', blank=True, null=True)
    zones = models.ManyToManyField('self', through='ZoneZone', blank=True, verbose_name='Vedi anche') # new: 130327
    web = models.TextField(verbose_name='Siti web', blank=True, help_text='uno per riga')

    # da geodjango/world/models
    shape_area = models.FloatField('Area', blank=True, null=True)
    shape_len = models.FloatField('Perimetro', blank=True, null=True)
    geom = geomodels.MultiPolygonField('Geometria', srid=srid_ISTAT, blank=True, null=True)
    # objects = geomodels.GeoManager()
    # campi originali
    pois = models.ManyToManyField('Poi', related_name='zone_pois', through='PoiZone')
    careof = models.ForeignKey('Poi', models.SET_NULL, related_name='zone_careof', verbose_name='A cura di', blank=True, null=True)
    modified = models.DateTimeField(verbose_name='Mod. il', auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = "zona"
        verbose_name_plural = "zone"
        ordering = ['zonetype', 'id',]

    def name_with_code(self):
        # return u'%s - %s' % (self.code, self.name)
        name = self.name
        if self.zonetype and self.zonetype.id in [1, 7]:
            prefix = ''
        else:
            prefix = self.code
        return '%s %s' % (prefix, name)

    # deprecated
    def zone(self):
        return self.name_with_code()

    def __str__(self):
        return self.name_with_code()

    # def pretty_name(self):
    def pretty_name(self, language='it'):
        name = self.name
        if self.zonetype.id in [1, 7]:
            prefix = ''
        else:
            # prefix = self.zonetype.getName().capitalize()
            prefix = self.zonetype.getName(language=language).capitalize()
        return '%s %s' % (prefix, name)

    def type_label(self):
        if self.zonetype_id == 3:
            return zone_prefix_dict[self.code[0]][1]
        else:
            return self.zonetype.name

    def type_label_plural(self):
        if self.zonetype_id == 3:
            return zone_prefix_dict[self.code[0]][2]
        else:
            return self.zonetype.name_plural

    # MMR new
    def zone_parent(self):
        zone_code_list = self.code.split('.')
        zone_prefix = zone_code_list[0]
        if zone_prefix == 'PR':
            return 'LAZIO'
        elif zone_prefix in ['Q','R','M','S','RM','ZU','Z','V','P']:
            return 'ROMA'
        elif zone_prefix == 'COM':
            macrozones=Zone.objects.filter(zonetype_id=0, zones=self)
            return macrozones[0].name
        else:
            macrozones=Zone.objects.filter(zonetype_id=0, pro_com=self.pro_com)
            if macrozones:
                return macrozones[0].name
            return 'LAZIO'

    # vedi metodo PoiAdmin.save_model
    def can_edit(self, request):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if not user.is_staff:
            return False
        careof_id = self.careof_id
        if careof_id:
            orgs = Poi.objects.filter(members=user)
            for org in orgs:
                if org.id == careof_id:
                    return True
        return False

    def get_map_label(self):
        if self.zonetype.id == MACROZONE:
            return self.name
        elif self.zonetype.id == TOPOZONE:
            return '%s-%s' % (self.code, self.name)
        else:
            return self.code

    def safe_code(self):
        return self.code.replace('.', '')

    # deprecated
    def get_url(self):
        return '/pois/zone/%s/' % self.id

    def has_geom(self):
        return self.geom and True or ''

    def geom_OSM(self):
        if self.has_geom():
            return self.geom.transform(srid_OSM, clone=True)
        return ''

    def centroid_OSM(self):
        centroid = self.geom.centroid.transform(srid_OSM, clone=True)
        return centroid

    def make_dict(self, list_item=False):
        zone_dict = {}
        zone_dict['id'] = self.id
        zone_dict['code'] = self.code
        zone_dict['name'] = self.name
        zone_dict['slug'] = self.slug
        #20180518 MMR - zone_dict['url'] = '/indice-zona/%s/' % self.slug
        zone_dict['url'] = '/risorse-utili-%s/' % self.slug
        zone_dict['safe_code'] = self.safe_code()
        zone_dict['zonetype_id'] = self.zonetype_id
        # MMR non utilizzato - zone_dict['zonetype_name_plural']= self.zonetype.name_plural
        zone_dict['zonetype_label']= self.type_label()
        # MMR non utilizzato - zone_dict['zonetype_label_plural']= self.type_label_plural()
        zone_dict['label'] = self.get_map_label()
        if not list_item:
            zone_dict['short'] = self.short
            zone_dict['has_geom'] = self.has_geom()
            zone_dict['geom'] = zone_dict['has_geom'] and self.geom_OSM().geojson or ''
            zone_dict['centroid'] = zone_dict['has_geom'] and self.centroid_OSM().geojson or ''
        return zone_dict

    def get_neighbours(self, max_distance=1, visited=None, zonetype=None):
        """ returns the zones overlapping self and those adjacent to self (with exceptions) """
        # print self, max_distance, visited
        if not visited:
            visited = []
        zones = []
        # for zone in self.zones.all():
        for zonezone in self.zonezone_set.all(): # see http://stackoverflow.com/questions/3368442
            to_zone = zonezone.to_zone
            if zonetype and to_zone.zonetype.id != zonetype:
                continue
            overlap = zonezone.overlap
            # distance = zonezone.distance
            if to_zone in visited:
                continue
            if to_zone.zonetype_id!=self.zonetype_id and overlap<50000:
                continue
            zones.append(to_zone)
            visited.append(to_zone)
            if max_distance > 1:
                zones = zones + to_zone.get_neighbours(max_distance=max_distance-1, visited=visited)
        return zones

    def overlaps(self, zonetypes=[1,2,6]):
        """ computes the zones overlapping self, based on geometry processing """
        overlaps = []
        for zone in Zone.objects.filter(zonetype__in=zonetypes, geom__overlaps=self.geom).order_by('zonetype'):
            overlap = zone.geom.intersection(self.geom).area
            overlaps.append([zone, overlap])
        return overlaps

    # def overlapping(self, zonetypes=[1,2,6], min_overlap=25000):
    def overlapping(self, zonetypes=None, min_overlap=25000):
        """ computes the zones overlapping self, based on geometry processing and using a threshold """
        if not self.has_geom():
            return []
        if zonetypes is None:
            zonetypes = [1, 3, 6, 7]
            if self.zonetype_id in zonetypes:
                zonetypes.remove(self.zonetype_id)
        # print 'zonetypes: ', zonetypes
        zones = []
        for zone in Zone.objects.filter(zonetype__id__in=zonetypes, geom__overlaps=self.geom).order_by('-zonetype__id', 'id'):
            # print 'zone: ', zone
            overlap = zone.geom.intersection(self.geom).area
            if overlap > min_overlap:
                zones.append(zone)
        return zones

    # def neighbouring(self, zonetypes=[1,2,6], min_overlap=25000):
    def neighbouring(self, zonetypes=None, min_overlap=25000):
        """ computes the neighbours of self, as those with small intersection with self (?) """
        if not self.has_geom():
            return []
        if zonetypes is None:
            zonetypes = [self.zonetype.id]
        """
        zones = []
        for zone in Zone.objects.filter(zonetype__in=zonetypes, geom__overlaps=self.geom).order_by('zonetype'):
            if self.zonetype_id==1 and zone.zonetype_id!=1: # 
                continue
            overlap = zone.geom.intersection(self.geom).area
            if overlap < min_overlap:
                zones.append(zone)
        """
        if zonetypes:
            # zones = Zone.objects.filter(zonetype__id__in=zonetypes, geom__distance_lte=(self.geom, 100)).order_by('-zonetype__id', 'id')
            zones = Zone.objects.filter(zonetype__id__in=zonetypes, geom__distance_lte=(self.geom, 100)).exclude(id=self.id).order_by('-zonetype__id', 'name')
        else:
            # zones = Zone.objects.filter(geom__distance_lte=(self.geom, 100)).order_by('-zonetype__id', 'id')
            zones = Zone.objects.filter(geom__distance_lte=(self.geom, 100)).exclude(id=self.id).order_by('-zonetype__id', 'name')
        neighbouring_zone_dict = defaultdict(list)
        for zone in zones:
            if zone.zonetype.id == 6: 
                neighbouring_zone_dict['0'].append(zone)
            else:
                neighbouring_zone_dict[zone.code[0]].append(zone)
        neighbouring_zone_list = []
        for key in ['M', 'R', 'Q', 'S', 'Z', 'C','0']:
            neighbouringlist = neighbouring_zone_dict.get(key, None)
            if neighbouringlist:
                neighbouring_zone_list.append(("%s %s" % (zone_prefix_dict[key][2], _("neighbouring")), zone_prefix_dict[key][1], neighbouringlist))
        return neighbouring_zone_list

    def list_subzones(self, zonetype_id=None):
        """ return the sub-zones of a macro-zone as a list of items (type, sublist) """
        if zonetype_id:
            subzones = self.zones.filter(zonetype_id=zonetype_id).order_by('name')
        else:
            subzones = self.zones.all().order_by('name')
        subzone_dict = defaultdict(list)
        for subzone in subzones:
            subzone_dict[subzone.code[0]].append(subzone)
        subzone_list = []
        for key in ['R', 'Q', 'S', 'Z']:
            sublist = subzone_dict.get(key, None)
            if sublist:
                subzone_list.append((zone_prefix_dict[key][2], zone_prefix_dict[key][1], sublist))
        return subzone_list

    def sametype_zones(self, include_roma=False):
        return Zone.objects.filter(zonetype_id=self.zonetype.id)

    def type_subzones(self, zonetype_id=7):
        return self.zones.filter(zonetype_id=zonetype_id)

    def friendly_url(self):
        return '/zona/%s/' % self.slug

    def get_macrozone_slug(self):
        zones = self.zones.filter(zonetype_id=0, id__gt=90)
        if zones:
            return zones[0].slug
        return None

    def render_web(self):
        lines = self.web.split('\n')
        html = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            words = line.split()
            url = words[0]
            if not url:
                continue
            if not url.startswith('http'):
                url = 'http://%s' % url
            label = len(words)>1 and ' '.join(words[1:]) or ''
            title = 'vai alla pagina web'
            html.append('<a href="%s" title="%s">%s</a>' % (url, title, label or url))
        return '<br/>\n'.join(html)

def split_topo_zones(zones):
    zone_dict = defaultdict(list)
    for zone in zones:
        # zone_dict[zone.code[0]].append(zone)
        zone_dict[zone['code'][0]].append(zone)
    split_list = []
    for key in ['R', 'Q', 'S', 'Z']:
        sublist = zone_dict.get(key, None)
        if sublist:
            split_list.append((zone_prefix_dict[key][2], sublist))
    # print subzone_dict
    return split_list

def list_all_zones():
    main_list = []
    zonetype_id = MACROZONE
    zonetype = Zonetype.objects.get(pk=zonetype_id)
    zone_list = Zone.objects.filter(zonetype=zonetype_id).order_by('name').values('id', 'code', 'name', 'slug')
    main_list.append([zonetype, zone_list])
    zonetype_id = MUNICIPIO
    zonetype = Zonetype.objects.get(pk=zonetype_id)
    zone_list = Zone.objects.filter(zonetype=zonetype_id).order_by('id').values('id', 'code', 'name', 'slug')
    main_list.append([zonetype, zone_list])
    zonetype_id = TOPOZONE
    zonetype = Zonetype.objects.get(pk=zonetype_id)
    zone_list = Zone.objects.filter(zonetype=zonetype_id).order_by('name').values('id', 'code', 'name', 'slug')
    # zone_list = [zone for zone in zone_list if zone.has_geom()]
    zone_list = split_topo_zones(zone_list)
    main_list.append([zonetype, zone_list])
    zonetype_id = CAPZONE
    zonetype = Zonetype.objects.get(pk=zonetype_id)
    zone_list = Zone.objects.filter(zonetype=zonetype_id).order_by('id').values('id', 'code', 'name', 'slug')
    main_list.append([zonetype, zone_list])
    return main_list

class TempZone(geomodels.Model):
    """ per uso temporaneo: (re-)importazione della geometria delle zone
        include un sottoinsieme dei campi di Zone """
    code = models.CharField('Codice', max_length=10)
    geom = geomodels.MultiPolygonField('Geometria', srid=srid_ISTAT, blank=True, null=True)
    # objects = geomodels.GeoManager()

@python_2_unicode_compatible
class ZoneZone(models.Model):
    from_zone = models.ForeignKey(Zone, models.CASCADE)
    to_zone = models.ForeignKey(Zone, models.CASCADE)
    overlap = models.IntegerField('Overlap area', blank=True, null=True, default=0)
    distance = models.IntegerField('Distance', blank=True, null=True, default=0)

    class Meta:
        verbose_name = "relazione zona-zona"
        verbose_name_plural = "relazioni zona-zona"
        db_table = 'pois_zonezone'
        auto_created = Zone

    def __str__(self):
        return '%s: vedi %s' % (self.from_zone.zone(), self.to_zone.zone())

def ZoneZone_populate(zonetypes=[1,3,6], skip=0):
    """ populate the class ZoneZone based on the topology of the instances of Zone """
    n_types = len(zonetypes)
    zones = Zone.objects.filter(zonetype__in=zonetypes).order_by('zonetype', 'id')
    n = len(zones)
    # print ('n = %d' % n)
    j = 0
    for i in range(n):
        if skip and i<skip:
            continue
        from_zone = zones[i]
        # print 'i = %d, %s' % (i, from_zone.code)
        from_geom = from_zone.geom
        if not from_geom:
            continue
        fanout = from_zone.zones.all()
        for to_zone in zones[i+1:n]:
            if n_types>1 and to_zone.zonetype==from_zone.zonetype:
                continue
            if not to_zone in fanout:
                to_geom = to_zone.geom
                if not to_geom:
                    continue
                distance = to_geom.distance(from_geom)
                if distance > 100:
                    continue
                overlap = to_geom.intersection(from_geom).area
                # if (not overlap) and distance > 100:
                if not overlap:
                    continue
                if from_zone.zonetype_id!=to_zone.zonetype_id and not (overlap>50000):
                    continue
                j += 1
                zz = ZoneZone(from_zone=from_zone, to_zone=to_zone, overlap=int(overlap), distance=int(distance))
                zz.save()
                zz = ZoneZone(from_zone=to_zone, to_zone=from_zone, overlap=int(overlap), distance=int(distance))
                zz.save()
                # print (j, from_zone.code, to_zone.code, int(overlap), int(distance))

@python_2_unicode_compatible
class Route(geomodels.Model):
    code = models.CharField('Codice', max_length=10, blank=True, null=True)
    name = models.CharField('Nome', max_length=100)
    slug = AutoSlugField(unique=True, populate_from='name', editable=True)
    short = models.CharField(verbose_name='In breve', max_length=200, null=True, blank=True)
    description = models.TextField(verbose_name='Descrizione', blank=True, null=True)
    web = models.TextField(verbose_name='Siti web', blank=True, help_text='uno per riga')
    coords = models.TextField(verbose_name='Coordinate', blank=True, null=True)
    geom = geomodels.MultiLineStringField('Geometria', srid=srid_GPS, blank=True, null=True)
    # objects = geomodels.GeoManager()
    width = models.IntegerField('Larghezza (m)', blank=True, null=True, default=200)
    pois = models.ManyToManyField('Poi', related_name='poi_route', through='PoiRoute')
    modified = models.DateTimeField(verbose_name='Mod. il', auto_now=True, blank=True, null=True)
    state = models.IntegerField(verbose_name='Stato', choices=STATE_CHOICES, default=0, null=True)

    class Meta:
        verbose_name = "itinerario"
        verbose_name_plural = "itinerari"
        ordering = ['id',]

    def __str__(self):
        return self.name

    def friendly_url(self):
        return '/itinerario/%s/' % self.slug

    def can_edit(self, request):
        user = request.user
        if not user.is_authenticated:
            return False
        return user.is_superuser or user.is_staff

    def has_geom(self):
        return self.geom and True or ''

    def geom_OSM(self):
        if self.has_geom():
            return self.geom.transform(srid_OSM, clone=True)
        return ''

    def get_near_pois(self, distance=200):
        geo_query = Q(point__distance_lt=(self.geom, D(m=distance)))
        state_query = Q(state=1)
        pois = Poi.objects.filter(geo_query & state_query).order_by('name')
        return pois

    def make_dict(self, list_item=False):
        route_dict = {}
        route_dict['id'] = self.id
        route_dict['code'] = self.code
        route_dict['name'] = self.name
        route_dict['slug'] = self.slug
        route_dict['url'] = '/itinerario/%s/' % self.slug
        if not list_item:
            route_dict['short'] = self.short
            route_dict['has_geom'] = self.has_geom()
            route_dict['geom'] = route_dict['has_geom'] and self.geom_OSM().geojson or ''
            route_dict['centroid'] = route_dict['has_geom'] and self.geom.centroid.geojson or ''
            route_dict['pois'] = self.get_near_pois(distance=self.width/2)
        return route_dict

def update_route_coordinates(sender, **kwargs):
    route = kwargs['instance']
    if not route.geom:
        if route.coords:
            cc = route.coords.split()
            coords = []
            for longlat in cc:
                longlat = longlat.split(',')
                longlat = [float(longlat[0]), float(longlat[1])]
                coords.append(longlat)
            linestring = LineString(coords)
            route.geom = MultiLineString([linestring], srid=srid_GPS)
            route.save()        

post_save.connect(update_route_coordinates, sender=Route)

@python_2_unicode_compatible
class Odonym(models.Model):
    name = models.CharField(max_length=60)
    slug = AutoSlugField(unique=True, populate_from='name', editable=True)
    short = models.CharField(verbose_name='In breve', max_length=120, null=True, blank=True)
    description = models.TextField(verbose_name='Descrizione', blank=True, null=True)
    web = models.TextField(verbose_name='Siti web', blank=True, help_text='uno per riga')
    modified = models.DateTimeField(verbose_name='Mod. il', auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = "toponimo"
        verbose_name_plural = "toponimi"

    def __str__(self):
        return self.name

    def get_pois(self):
        return Poi.objects.filter(street=self)

    def get_zones(self):
        poi_list = Poi.objects.filter(street=self)
        zones = []
        zone_ids = []
        zones_zipcode = []
        zones_zipcode_ids = []
        for poi in poi_list:
            for zone in poi.zones.all():
                # MMR exclude ex municio
                if zone.zonetype.id != 1:
                    if not zone.id in zone_ids:
                        zones.append(zone)
                        zone_ids.append(zone.id)
            if poi.zipcode:
                for zone in Zone.objects.filter(code=poi.zipcode):
                    if not zone.id in zones_zipcode_ids:
                        zones_zipcode.append(zone)
                        zones_zipcode_ids.append(zone.id)
        # MMR zones.sort(lambda x,y: cmp(reordered_zonetype(x.zonetype.id)*10000+x.id, reordered_zonetype(y.zonetype.id)*10000+y.id))
        zones.sort(key=lambda x: reordered_zonetype(x.zonetype.id)*10000+x.id)
        zones_zipcode.sort(key=lambda x: reordered_zonetype(x.zonetype.id)*10000+x.id)
        return zones, zones_zipcode

    def position(self):
        pois = self.get_pois()
        n = lat = lon = 0
        if pois:
            for poi in pois:
                try:
                    point = poi.get_point()
                    lon += point.x
                    lat += point.y
                    n += 1
                except:
                    pass
        if n:
            latitude = float("{0:.5f}".format(lat/n))
            longitude = float("{0:.5f}".format(lon/n))
        else:
            latitude = roma_lat
            longitude = roma_lon
        return {'latitude': latitude, 'longitude': longitude,}

    def fw_core_location(self):
        return {'wgs84': self.position()}

    def friendly_url(self):
        return '/toponimo/%s/' % self.slug

    def can_edit(self, request):
        user = request.user
        if user.is_superuser:
            return True
        return False

@python_2_unicode_compatible
class Tag(models.Model):
    name_en = models.CharField(max_length=40, blank=True)
    # name_it = models.CharField(max_length=40, blank=True)
    name = models.CharField(max_length=40, blank=True)
    slug = AutoSlugField(unique=True, populate_from='name', editable=True)
    weight = models.IntegerField('Importanza', blank=True, null=True, default=1)
    color = models.CharField('Colore', max_length=20, blank=True, null=True)
    tags = models.ManyToManyField('self', through='TagTag', blank=True) # new: 130308
    modified = models.DateTimeField(verbose_name='Mod. il', auto_now=True, blank=True, null=True)
    short = models.CharField(verbose_name='Descriz. breve', max_length=120, null=True, blank=True)
    
    class Meta:
        verbose_name = "tag"
        verbose_name_plural = "tags"
        # ordering = ('weight', 'name_it',)
        ordering = ('weight', 'name',)

    def getName(self, language='it'):
        """
        name = language.startswith('it') and self.name_it or self.name_en
        return name
        """
        return self.name

    def __str__(self):
        # return self.getName()
        return self.name

    """
    def name(self, language='it'):
        return self.getName(language)

    def slug(self):
        # return slugify(self.name_it)
        return slugify(self.name)
    """

    def friendly_url(self):
        return '/tema/%s/' % self.slug

    def make_dict(self):
        tag_dict = { 'id': self.id, 'name': self.name, 'slug': self.slug, 'url': self.friendly_url(), 'short': self.short }
        return tag_dict

@python_2_unicode_compatible
class TagTag(models.Model):
    from_tag = models.ForeignKey(Tag, models.CASCADE)
    to_tag = models.ForeignKey(Tag, models.CASCADE)

    class Meta:
        verbose_name = "relazione tag-tag"
        verbose_name_plural = "relazioni tag-tag"
        db_table = 'pois_tagtag'
        auto_created = Tag

    def __str__(self):
        return '%s in %s' % (self.from_tag.getName(), self.to_tag.getName())

@python_2_unicode_compatible
class Poitype(models.Model):
    # klass = models.CharField(max_length=8, unique=True, blank=True, null=True)
    klass = models.CharField(max_length=10, unique=True, blank=True, null=True)
    name_en = models.CharField(max_length=80, blank=True)
    # name_it = models.CharField(max_length=80, blank=True)
    name = models.CharField(max_length=80, blank=True)
    icon = models.CharField(max_length=20, blank=True, null=True)
    color = models.CharField(max_length=20, blank=True, null=True)
    active = models.BooleanField(default=False)
    tags = models.ManyToManyField('Tag', through='PoitypeTag', blank=True) #MMR 20181701 tolto null=True # new: 130308
    # slug = AutoSlugField(unique=True, populate_from='name_it', editable=True)
    slug = AutoSlugField(unique=True, populate_from='name', editable=True)
    modified = models.DateTimeField(verbose_name='Mod. il', auto_now=True, blank=True, null=True)
    short = models.CharField(verbose_name='Descriz. breve', max_length=120, null=True, blank=True)

    class Meta:
        verbose_name = "tipo di risorsa"
        verbose_name_plural = "tipi di risorsa"
        ordering = ['klass',]

    def getCode(self):
        return self.klass

    def getName(self, language='it'):
        """
        name = language.startswith('it') and self.name_it or self.name_en
        return name
        """
        return self.name

    def __str__(self):
        """
        return self.getName()
        """
        return self.name

    def get_names(self):
        content_type = ContentType.objects.get(model='poitype')
        keyvalues = KeyValue.objects.filter(content_type_id=content_type.id, object_id=self.id)
        names = {}
        for keyvalue in keyvalues:
            names[keyvalue.language] = keyvalue.value
        return names
    
    def fixed_length_code(self, language='it'):
        # return '%s - %s' % (self.getCode().replace(' ', '&nbsp;'), self.getName())
        return '%s - %s' % (self.klass, self.getName(language=language))

    def get_icon(self):
        klass = self.klass
        category = klass[:4]
        # return poi_icon_map.get(klass, poi_icon_map.get(category, 'flag'))
        icon = poi_icon_map.get(klass, poi_icon_map.get(category, None))
        if icon:
            if isinstance(icon, (list, tuple)):
                return {'name': icon[0], 'color': icon[1]}
            else:
                return {'name': icon, 'color': 'red'}
        else:
            return {'name': 'flag', 'color': 'red'}

    def icon_name(self):
        return self.get_icon()['name']

    def get_themes(self):
        themes = self.tags.filter(weight__gt=10)
        return themes

    def friendly_url(self):
        return '/categoria/%s/' % self.slug

    def sub_types(self, return_klasses=False):
        poitypes = Poitype.objects.filter(klass__startswith=self.klass).exclude(klass=self.klass)
        if return_klasses:
            return [p.klass for p in poitypes]
        else:
            return poitypes

    def make_dict(self):
        # poitype_dict = { 'name': self.name,  'slug': self.slug, 'active': self.active, 'icon': self.icon }
        poitype_dict = { 'name': self.name,  'slug': self.slug, 'active': self.active, 'icon': self.get_icon(), 'short': self.short}
        return poitype_dict

@python_2_unicode_compatible
class PoitypeTag(models.Model):
    poitype = models.ForeignKey(Poitype, models.CASCADE)
    tag = models.ForeignKey(Tag, models.CASCADE)

    class Meta:
        verbose_name = "relazione tiporisorsa-tag"
        verbose_name_plural = "tiporisorsa-tag"
        db_table = 'pois_poitypetag'
        auto_created = Poitype

    def __str__(self):
        return '%s has tag %s' % (self.poitype.getName(), self.tag.getName())

def get_chain_poi(item, list_pois):
    poipois = PoiPoi.objects.filter(reltype_id = 2, from_poi=item)
    for poipoi in poipois:
        if not poipoi.to_poi in list_pois:
            list_pois.append(poipoi.to_poi)
            get_chain_poi(poipoi.to_poi,list_pois)
    return list_pois

@python_2_unicode_compatible
class Poi(geomodels.Model):
    name = models.CharField(verbose_name='Nome', max_length=100)
    poitype = models.ForeignKey(Poitype, models.PROTECT, related_name='poi_poitype', to_field='klass', verbose_name='Categoria primaria', null=True, blank=True)
    moretypes = models.ManyToManyField(Poitype, related_name='poi_moretypes', through='PoiPoitype', blank=True, verbose_name='Altre categorie')
    code = models.CharField('Codice', max_length=20, blank=True, null=True)
    short = models.CharField(verbose_name='Descriz. breve', max_length=120, null=True, blank=True)
    description = models.TextField(verbose_name='Descrizione', blank=True)   
    tags = models.ManyToManyField('Tag', through='PoiTag') # new: 130308
    othertags = models.CharField(verbose_name='Altre keyword', max_length=100, blank=True)
    zones = models.ManyToManyField('Zone', through='PoiZone', blank=True, verbose_name='Zone')
    routes = models.ManyToManyField('Route', through='PoiRoute', blank=True, verbose_name='Route')
    pro_com = models.IntegerField('Comune', blank=True, null=True, default=58091)
    street_address = models.CharField(verbose_name='Indirizzo', max_length=100, blank=True)
    street = models.ForeignKey(Odonym, models.PROTECT, related_name='poi_street', verbose_name='Toponimo (es: Via Po)', blank=True, null=True)
    housenumber = models.CharField(verbose_name='Civico', max_length=16, blank=True)
    zipcode = models.CharField('CAP', max_length=5, blank=True)
    latitude = models.FloatField('Latitudine', blank=True, null=True)
    longitude = models.FloatField('Longitudine', blank=True, null=True)    # Geo Django field to store a point (vedi www.chicagodjango.com/blog/geo-django-quickstart)
    # point = geomodels.PointField(verbose_name='Posizione', help_text="", srid=srid_ISTAT, blank=True, null=True)
    point = geomodels.PointField(verbose_name='Posizione', help_text="", srid=srid_GPS, blank=True, null=True)
    # You MUST use GeoManager to make Geo Queries
    # objects = geomodels.GeoManager()
    phone = models.TextField(verbose_name='Numeri telefonici', blank=True, help_text='uno per riga')
    email = models.TextField('Indirizzi email', blank=True, help_text='uno per riga')
    web = models.TextField(verbose_name='Indirizzi web', blank=True, help_text='uno per riga')
    video = models.TextField(verbose_name='Indirizzi video', blank=True, help_text='uno per riga')
    feeds = models.TextField(verbose_name='Indirizzi di feeds', blank=True, help_text=' rss e atom, uno per riga')
    # pois = models.ManyToManyField('self', through='PoiPoi', verbose_name='Vedi anche') # new: 130327
    pois = models.ManyToManyField('self', through='PoiPoi', symmetrical=False, verbose_name='Risorse correlate') # new: 130610 no symmetrical

    notes = models.TextField(verbose_name='Note', blank=True, null=True)   
    sourcetype = models.ForeignKey(Sourcetype, models.PROTECT, verbose_name='Tipo di fonte', blank=True, null=True)
    """
    source = models.ForeignKey('self', related_name='poi_source', verbose_name='Fonte', blank=True, null=True)
    sourceel = models.PositiveSmallIntegerField(verbose_name='Fonte', blank=True, null=True)
    sourceid = models.IntegerField(verbose_name='Codice fonte', blank=True, null=True)
    """
    source = models.TextField(verbose_name='Fonte', blank=True)
    owner = models.ForeignKey(User, models.SET_NULL, related_name='poi_owner', blank=True, null=True)
    contributor = models.CharField(verbose_name='Contributo di', max_length=20, blank=True)
    creator = models.CharField(verbose_name='Compilatore', max_length=20, blank=True)
    lasteditor = models.ForeignKey(User, models.SET_NULL, related_name='poi_lasteditor', blank=True, null=True, verbose_name='Mod. da')
    modified = models.DateField(verbose_name='Mod. il', auto_now=True, blank=True, null=True)
    # aggiunto 130606
    host = models.ForeignKey('self', models.SET_NULL, related_name='poi_host', verbose_name='Ospitato da', blank=True, null=True)
    logo = models.ImageField(upload_to='logos', null=True, blank=True, verbose_name='Logo (immagine)')
    slug = AutoSlugField(unique=True, populate_from='name', editable=True, blank=True, null=True)
    # aggiunto 130808
    members = models.ManyToManyField(User, related_name='poi_members', through='PoiMember', symmetrical=False, verbose_name='Membri')
    careof = models.ForeignKey('self', models.SET_NULL, related_name='poi_careof', verbose_name='A cura di', blank=True, null=True)
    KIND_CHOICES = (
        (0, 'servizio'),
        (1, 'struttura'),
        (2, 'consorzio'),
        (3, 'associazione di categoria'),)
    kind = models.IntegerField(verbose_name='Tipo', choices=KIND_CHOICES, default=1, null=True)
    PARTNERSHIP_CHOICES = (
        (0, '-'),
        (1, 'socio'),
        (2, 'partner'),
        (3, 'sponsor'),)
    partnership = models.IntegerField(verbose_name='Partnership', choices=PARTNERSHIP_CHOICES, default=0, null=True)
    """
    STATE_CHOICES = (
        (0, 'new'),
        (1, 'ok'),
        (2, 'off'),)
    """
    state = models.IntegerField(verbose_name='Stato', choices=STATE_CHOICES, default=0, null=True)
    #180405 MMR
    TYPECARD_CHOICES = (
        (0, 'free'),
        (1, 'a pagamento'),
        (2, 'pubblica'),
        (3, 'promozione'),)
    typecard = models.IntegerField(verbose_name='Scheda', choices=TYPECARD_CHOICES, default=0, null=True)
    created = models.DateField(verbose_name='Creata il', auto_now_add=True, blank=True, null=True)
    
    class Meta:
        verbose_name = "risorsa"
        verbose_name_plural = "risorse"

    def poi(self):
        # return u'%s (%s)' % (self.name, self.poitype.getName())
        return self.poitype and '%s (%s)' % (self.name, self.poitype.getName()) or self.name

    def __str__(self):
        return self.poi()

    def safe_name(self):
        # return self.name.replace("'","").replace('"','')
        # return self.name.replace('"','')
        return self.name.replace('"','').replace("'", "\'")

    def getName(self):
        return self.name
    
    def getLogo(self):
        return self.logo

    def prefixed_name(self):
        name = self.safe_name()
        poitype = self.poitype
        if not poitype:
            return name
        klass = poitype.klass
        prefix_item = poi_klass_prefixes.get(klass, None)
        prefix = ''
        print (prefix_item)
        if prefix_item:
            prefix = prefix_item[0]
            name_lower = name.lower()
            for mark in prefix_item[1]:
                if name_lower.count(mark):
                    prefix = ''
                    break
            if prefix:
                # name = '%s %s' % (prefix.capitalize(), name)
                name = '%s %s' % (prefix, name)
        return name
        
    def getTypecard(self):
        return self.typecard
        
    # vedi metodo PoiAdmin.save_model
    def can_edit(self, request):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if not user.is_staff:
            return False
        if user == self.owner:
            return True
        careof_id = self.careof_id
        if careof_id:
            orgs = Poi.objects.filter(members=user)
            for org in orgs:
                if org.id == careof_id:
                    return True
        return False

    def get_themes(self, return_ids=False):
        # tags = Tag.objects.filter(weight__gt=10, poitype=self.poitype)
        tags = self.tags.all()
        if return_ids:
            return [tag.id for tag in tags]
        else:
            return tags

    def get_themes_indirect(self, return_ids=False):
        tags = []
        if self.poitype:
            poitype_ids = [self.poitype.id]
            tags = Tag.objects.filter(weight__gt=10, poitype__in=poitype_ids).distinct()
        if return_ids:
            return [tag.id for tag in tags]
        else:
            return tags

    def get_all_themes(self, return_names=False):
        tags = list(self.get_themes())
        tags.extend(list(self.get_themes_indirect()))
        if return_names:
            return ', '.join([tag.name for tag in tags])
        else:
            return tags

    def get_affiliation(self):
        """
        poipois = PoiPoi.objects.filter(from_poi=self)
        for poipoi in poipois:
            if poipoi.reltype_id == 1:
                return poipoi.to_poi
        """
        poipois = PoiPoi.objects.filter(from_poi=self, reltype_id = 1)
        for poipoi in poipois:
                return poipoi.to_poi
        return None

    def get_affiliations(self):
        affiliations = []
        """
        poipois = PoiPoi.objects.filter(from_poi=self)
        return [poipoi.to_poi for poipoi in poipois if poipoi.reltype_id == 1]
        """
        poipois = PoiPoi.objects.filter(from_poi=self, reltype_id = 1)
        return [poipoi.to_poi for poipoi in poipois]

    def get_chain_pois(self):
        return get_chain_poi(self,[])

    def get_url(self):
        return '/pois/%s/' % self.id

    def friendly_url(self):
        return '/risorsa/%s/' % self.slug

    def GPS(self):
        # return str(self.point)
        return str(self.get_point())

    def get_point(self):
        point = self.point
        if not point and self.host:
            point = self.host.point
        return point

    def has_point(self):
        point = self.get_point()
        return point and point.x and point.y and True or ''

    def point_OSM(self):
        point = self.get_point()
        if point:
            return point.transform(srid_OSM, clone=True)
        return ''
  
    def position(self):
        try:
            point = self.get_point()
            latitude = float("{0:.5f}".format(point.y))
            longitude = float("{0:.5f}".format(point.x))
        except:
            latitude = roma_lat
            longitude = roma_lon
        return {'latitude': latitude, 'longitude': longitude,}

    def get_comune(self):
        try:
            zone = Zone.objects.get(pro_com=self.pro_com)
            return zone.name, zone.slug
        except:
            return 'Roma', 'roma'
            
    def fw_core_location(self):
        return {'wgs84': self.position()}

    def fw_core_category(self):
        # return self.poitype.slug
        return self.poitype_id # poitype.klass

    def fw_core_name(self):
        return self.name

    """
    def fw_core_label(self):
        return {'_def': 'it', 'it': self.name,}
    """

    def get_short_dict(self):
        content_type = ContentType.objects.get(model='poi')
        keyvalues = KeyValue.objects.filter(content_type_id=content_type.id, object_id=self.id, field='short')
        short_dict = {}
        for keyvalue in keyvalues:
            short_dict[keyvalue.language] = keyvalue.value
        return short_dict

    def fw_core_description(self):
        description = self.get_short_dict()
        description['_def'] = 'it'
        return description

    def fw_core_source(self):
        return {'name': 'Link srl', 'website': 'http://www.romapaese.it', 'id': self.creator.username, 'license': '',}

    def fw_core_last_update(self):
        epoch = datetime.datetime.utcfromtimestamp(0)
        return {'timestamp': (datetime.datetime(self.modified) - epoch).total_seconds() * 1000.0, 'responsible': self.lasteditor.username,}

    def fw_contact_postal(self):
        ## return [self.street_address(), '%s Roma' % self.zipcode]
        # return [self.street_address(), '%s %s' % (self.zipcode, self.get_comune())]
        return [self.get_street_address(), '%s %s' % (self.zipcode, self.get_comune())]

    def fw_contact_mailto(self):
        lines = self.email.split('\n')
        mailto = []
        for line in lines:
            line = line.replace('\r','').strip()
            if line:
                mailto.append(line)
        return mailto and '|'.join(mailto) or ''

    def fw_contact_phone(self):
        lines = self.phone.split('\n')
        phone = []
        for line in lines:
            line = line.replace('\r','').strip()
            pieces = line.split()
            if len(pieces)>=2 and len(pieces[0])<=3 and pieces[0].isdigit() and pieces[1][0].isdigit():
                line = [pieces[0]+pieces[1]]
                line.extend(pieces[2:])
                line = ' '.join(line)
            if line:
                phone.append(line)
        return phone and '|'.join(phone) or ''

    def fw_fairvillage_web(self):
        lines = self.web.split('\n')
        web = []
        for line in lines:
            line = line.replace('\r','').strip()
            if line:
                web.append(line)
        return web and '|'.join(web) or ''

    def get_description_dict(self):
        content_type = ContentType.objects.get(model='poi')
        keyvalues = KeyValue.objects.filter(content_type_id=content_type.id, object_id=self.id, field='description')
        description_dict = {}
        for keyvalue in keyvalues:
            description_dict[keyvalue.language] = keyvalue.value
        return description_dict

    def fw_fairvillage_text(self):
        text = self.get_description_dict()
        text['_def'] = 'it'
        return text

    def fw_fairvillage_video(self):
        return self.video

    def fw_fairvillage_hosted_by(self):
        return self.host and self.host.name or ''

    def compute_macrozone(self):
        macrozone = Zone(id=0, code='XX', name='temporary')
        zones = self.zones.all()
        if not zones:
            return macrozone
        geoms = [zone.geom for zone in zones]
        macro_geom = geoms[0]
        for geom in geoms[1:]:
            macro_geom = macro_geom.union(geom)
        try:
            macrozone.geom = MultiPolygon(macro_geom)
        except:
            macrozone.geom = macro_geom
        return macrozone

    def macrozone_geom_OSM(self):
        macrozone = self.compute_macrozone()
        if macrozone.geom:
            # print macrozone.geom
            return macrozone.geom.transform(srid_OSM, clone=True)

    def lat_long(self):
        point = self.get_point()
        if point:
            ll = [point.y, point.x]
        else:
            ll = [self.latitude or 0.0, self.longitude or 0.0]
        return '%f, %f' % (ll[0], ll[1])

    def get_icon(self):
        # return self.poitype.get_icon()
        return self.poitype and self.poitype.get_icon() or {'name': 'flag', 'color': 'red'}

    def icon_name(self):
        return self.get_icon()['name']

    def icon_color(self):
        return self.get_icon()['color']

    def street_name(self):
        # street = self.street_object
        street = self.street
        if street:
            return street.name
        else:
            return ''

    """
    def street_address(self):
        return '%s %s' % (self.street_name(), self.housenumber)
    """
    def get_street_address(self):
        # return self.street_address or '%s %s' % (self.street_name(), self.housenumber)
        if self.street_address:
            return self.street_address
        street_address = self.street_name()
        if self.housenumber:
            street_address = '%s, %s' % (street_address, self.housenumber)
        return street_address

    def cap_zone(self):
        cap = self.zipcode
        if cap:
            return Zone.objects.get(code=cap)
        else:
            return None

    def update_zones(self, zonetypes=[1, 3, 7,]):
        current_zones = self.zones.all()
        current_ids = [zone.id for zone in current_zones]
        target_zones = []
        point = self.get_point()
        if point:
            target_zones = Zone.objects.filter(zonetype__id__in=zonetypes, geom__contains=point)
        target_ids = [zone.id for zone in target_zones]
        for zone in self.zones.all():
            if zone.id not in target_ids:
                print ('removing ..', zone)
                self.zones.remove(zone)
        for zone in target_zones:
            if zone.id not in current_ids:
                self.zones
                print ('adding ..', zone)
                self.zones.add(zone)

    def clean_list(self, text):
        items = []
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            items.append(line)
        return items

    def clean_phones(self):
        return self.clean_list(self.phone)

    def clean_urls(self, text, prefix, protocol):
        items = []
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            words = line.split()
            l = len(words)
            address = words[0]
            label = address
            # if not address.startswith(prefix):
            if not address.startswith(prefix) and not address.startswith('/'):
                address = protocol + address
            if l > 1:
                label = ' '.join(words[1:])
            item = [address, label]
            items.append(item)
        return items

    def clean_emails(self):
        return self.clean_urls(self.email, 'mailto', 'mailto:')

    def clean_webs(self):
        return self.clean_urls(self.web, 'http', 'http://')

    def safe_email(self):
        email = self.email
        if email and not email.startswith('mailto'):
            email = 'mailto:'+email
        return email

    def safe_web(self):
        lines = self.web.split('\n')
        # url = ''
        urls = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            words = line.split()
            url = words[0]
            if not url:
                continue
            if not url.startswith('http'):
                url = 'http://%s' % url
            urls.append(url)
        # return url
        return urls

    def render_web(self):
        lines = self.web.split('\n')
        html = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            words = line.split()
            url = words[0]
            if not url:
                continue
            if not url.startswith('http'):
                url = 'http://%s' % url
            # if self.poitype.klass=='06340459' and url.count('vicariatusurbis') and url.count('page_id'):
            if self.poitype and self.poitype.klass=='06340459' and url.count('vicariatusurbis') and url.count('page_id'):
                label = 'pagina nel sito del Vicariato di Roma'
                title = 'vai alla %s' % label
            else:
                label = len(words)>1 and ' '.join(words[1:]) or ''
                title = 'vai al sito web di %s' % self.name
            html.append('<a href="%s" title="%s">%s</a>' % (url, title, label or url))
        return '<br/>\n'.join(html)

    def render_host(self):
        host = self.host
        if not host:
            return None
        return '<a href="%s">%s</a>' % (host.get_url(), host.prefixed_name())

    def get_video(self):
        urls = []
        if self.video:
            lines = self.video.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                words = line.split()
                url = words[0]
                if not url:
                    continue
                if url.startswith('http:'):
                    url = url.replace('http:','https:',6)
                elif not url.startswith('https'):
                    url = 'https://%s' % url
                urls.append(url)
        return urls
        
    def get_feeds(self):
        feeds = []
        if self.feeds:
            lines = self.feeds.split('\n')
            for line in lines:
                url = line.split('\n')[0].strip()
                if url:
                    d = feedparser.parse(url)
                    if d.feed and d.entries:
                        feeds.append(d)
        return feeds    

    # return blogs authored by users being members of this resource
    def get_blogs(self):
        return Blog.objects.filter(author__in=self.members.all())

    # return a dict with some resource data
    def make_dict(self, list_item=False):
        poi_dict = {}
        poi_dict['id'] = self.id
        poi_dict['name'] = self.getName().strip()
        poi_dict['safe_name'] = self.safe_name().strip()
        poi_dict['url'] = self.friendly_url()
        poi_dict['short'] = self.short or ''
        try:
            street = self.street
            poi_dict['street'] = street.id
            poi_dict['street_name'] = street.name
            poi_dict['street_url'] = street.friendly_url()
        except:
            poi_dict['street'] = 0
            poi_dict['street_name'] = ''
            poi_dict['street_url'] = ''
        poi_dict['number'] = self.housenumber
        poi_dict['street_address'] = self.get_street_address()
        poi_dict['cap'] = self.zipcode
        try:
            poi_dict['cap_zone'] = self.cap_zone().id
        except:
            poi_dict['cap_zone'] = 0
        poi_dict['comune'] = self.get_comune()
        poi_dict['icon'] = self.icon_name()
        poi_dict['color'] = self.icon_color()
        point_osm = self.point_OSM()
        if point_osm:
            poi_dict['point'] = point_osm.geojson
        else:
            poi_dict['point'] = ''
        if not list_item:
            poi_dict['slug'] = self.slug
            poi_dict['prefixed_name'] = self.prefixed_name()
            poi_dict['description'] = self.description or ''
            poi_dict['category'] = self.poitype and self.poitype.name or '-'
            poi_dict['phones'] = self.clean_phones()
            poi_dict['emails'] = self.clean_emails()
            poi_dict['webs'] = self.clean_webs()
            poi_dict['video'] = self.get_video()
            poi_dict['logo'] = self.logo and self.logo.url or ''
            if self.owner:
                poi_dict['owner'] = '%s %s' % (self.owner.first_name, self.owner.last_name)
            else:
                poi_dict['owner'] = ''
            careof = self.careof
            if careof:
                logo = careof.logo
                careof = { 'name': careof.name, 'url': careof.friendly_url(), 'web': careof.safe_web()[0], 'logo_url': logo and logo.url or ''}
            poi_dict['careof'] = careof
            poi_dict['modified'] = str(self.modified)
            host = self.host
            poi_dict['host_name'] = host and host.prefixed_name() or ''
            poi_dict['host_url'] = host and host.friendly_url() or ''
            poi_dict['routes'] = self.routes.all()
            """
            affiliation = self.get_affiliation()
            if affiliation:
                logo = affiliation.logo
                affiliation = { 'name': affiliation.name, 'url': affiliation.friendly_url(), 'logo': logo and logo.url or '' }
            poi_dict['affiliation'] = affiliation
            """
            affiliations = self.get_affiliations()
            poi_dict['affiliations'] = [{'name': affiliation.name, 'url': affiliation.friendly_url(), 'logo': affiliation.logo and affiliation.logo.url or '' } for affiliation in affiliations if affiliation.state == 1]
            """
            MMR temporaneamente disattivato
            blogs = self.get_blogs()
            if blogs:
                blogs = [{'title': blog.title, 'url': blog.friendly_url()} for blog in blogs]
            poi_dict['blogs'] = blogs
            """
            poi_dict['blogs'] = []
            poi_dict['state'] = STATE_CHOICES[self.state][1]
        return poi_dict
    
    def make_short_dict(self):
        poi_dict = {}
        poi_dict['id'] = self.id
        poi_dict['name'] = self.getName().strip()
        poi_dict['safe_name'] = self.safe_name().strip()
        poi_dict['url'] = self.friendly_url()
        poi_dict['slug'] = self.slug
        poi_dict['feeds'] = self.feeds
        poi_dict['webs'] = self.clean_webs()
        poi_dict['state'] = STATE_CHOICES[self.state][1]
        poi_dict['modified'] = str(self.modified)
        return poi_dict
"""
MMR 20181701 non utilizzato
    # riadattato da funzione javascript make_poi_el in zone_map.html
    def make_html_element(self):
        poi_dict = self.make_dict()
        s = <div class="row">\
                 <div class="span5"><a class="ele nameRes" title="visualizza risorsa" href="%s">%s</a></div>\
                 <div class="span5"><a class="ele" title="visualizza strada, piazza ..." href="%s">%s</a> - <a class="ele" title="visualizza zona CAP" href="/zona-cap/%s/">%s</a> %s</div>\
                 </div>\
                 <div class="row rowRes">\
                 <div class="span10" style="padding-left: 2px;">%s</div>\
                 </div>

        ## return s % (poi_dict['url'], poi_dict['name'], poi_dict['street_url'], poi_dict['street_name'], poi_dict['number'], poi_dict['cap'], poi_dict['cap'], poi_dict['short']);
        #return s % (poi_dict['url'], poi_dict['name'], poi_dict['street_url'], poi_dict['street_name'], poi_dict['number'], poi_dict['cap'], poi_dict['cap'], poi_dict['comune'], poi_dict['short']);
        return s % (poi_dict['url'], poi_dict['name'], poi_dict['street_url'], poi_dict['street_address'], poi_dict['cap'], poi_dict['cap'], poi_dict['comune'], poi_dict['short']);
"""
# @receiver(post_save, sender=Poi)
def update_poi_coordinates(sender, **kwargs):
    poi = kwargs['instance']
    if not poi.point:
        if poi.latitude and poi.longitude:
            poi.point = Point(poi.longitude, poi.latitude, srid=srid_GPS)
            poi.save()        

post_save.connect(update_poi_coordinates, sender=Poi)


@python_2_unicode_compatible
class PoiPoitype(models.Model):
    poi = models.ForeignKey(Poi, models.CASCADE)
    poitype = models.ForeignKey(Poitype, models.PROTECT)

    class Meta:
        verbose_name = "relazione risorsa-categoria secondaria"
        verbose_name_plural = "relazioni risorsa-categoria secondaria"
        db_table = 'pois_poipoitype'
        auto_created = Poi

    def __str__(self):
        return '%s in %s' % (self.poi.poi(), self.poitype.getName())
        
@python_2_unicode_compatible
class PoiZone(models.Model):
    poi = models.ForeignKey(Poi, models.CASCADE)
    zone = models.ForeignKey(Zone, models.PROTECT)

    class Meta:
        verbose_name = "relazione risorsa-zona"
        verbose_name_plural = "relazioni risorsa-zona"
        db_table = 'pois_poizone'
        auto_created = Poi

    def __str__(self):
        return '%s in %s' % (self.poi.poi(), self.zone.zone())

def PoiZone_clean(zonetypes=[0, 2, 3]):
    """ purce the class PoiZone (table pois_poizone) by zone type """
    PoiZone.objects.filter(zone__zonetype__in=zonetypes).delete()
    
def PoiZone_populate(zonetype=3, poitypes=[]):
    """ populate the class PoiZone based on the topological relationships """
    if poitypes:
        pois = Poi.objects.filter(poitype__klass__in=poitypes).order_by('poitype__klass', 'id')
    else:
        pois = Poi.objects.all().order_by('poitype__klass', 'id')
    n = len(pois)
    m = 0
    for i in range(n):
        poi = pois[i]
        # pnt = poi.point
        pnt = poi.get_point()
        if not pnt:
            continue
        zones = poi.zones.filter(zonetype__id=zonetype)
        if not zones:
            zones = Zone.objects.filter(zonetype__id=zonetype, geom__contains=pnt)
            if zones and len(zones)==1:
                zone = zones[0]
                pz = PoiZone(poi=poi, zone=zone)
                pz.save()
                m += 1
                # print (poi, zone)
    # print (n, m)

def PoiZone_spatialize_macrozones():
    macrozones = Zone.objects.filter(zonetype=0)
    for macrozone in macrozones:
        # geoms = [zone.geom for zone in macrozone.zones.all()]
        geoms = [zone.geom for zone in macrozone.zones.filter(zonetype=7)]
        macro_geom = geoms[0]
        for geom in geoms[1:]:
            macro_geom = macro_geom.union(geom)
        try:
            macrozone.geom = MultiPolygon(macro_geom)
        except:
            macrozone.geom = macro_geom
        macrozone.save()

@python_2_unicode_compatible
class PoiRoute(models.Model):
    poi = models.ForeignKey(Poi, models.CASCADE)
    route = models.ForeignKey(Route, models.PROTECT)
    order = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        verbose_name = "relazione risorsa-itinerario"
        verbose_name_plural = "relazioni risorsa-itinerario"
        db_table = 'pois_poiroute'
        auto_created = Poi

    def __str__(self):
        return '%s in %s' % (self.poi.name, self.route.name)

@python_2_unicode_compatible
class PoiTag(models.Model):
    poi = models.ForeignKey(Poi, models.CASCADE)
    tag = models.ForeignKey(Tag, models.CASCADE)

    class Meta:
        verbose_name = "relazione risorsa-tag"
        verbose_name_plural = "relazioni risorsa-tag"
        db_table = 'pois_poitag'
        auto_created = Poi

    def __str__(self):
        return '%s in %s' % (self.poi.poi(), self.tag.getName())

def make_zone_subquery(zone):
    if zone.zonetype_id == CAPZONE:
        q = Q(zipcode=zone.code)
    elif zone.zonetype_id == MACROZONE:
        subzones = zone.zones.filter(zonetype_id=MUNICIPIO)
        zone_ids = [subzone.id for subzone in subzones]
        q = Q(zones__in=zone_ids)
    else:
        q = Q(zones=zone)
    return q

def resources_by_theme(tag):
    categories = Poitype.objects.filter(tags=tag).values_list('klass', flat=True)
    resources = Poi.objects.filter(Q(poitype_id__in=categories) | Q(tags=tag)).filter(state=1).distinct().order_by('-id')
    return resources

def resources_by_theme_count(tag):
    categories = Poitype.objects.filter(tags=tag).values_list('klass', flat=True)
    n = Poi.objects.filter(Q(poitype_id__in=categories) | Q(tags=tag)).filter(state=1).distinct().count()
    return n

def resources_by_topo(zone):
    # resources = Poi.objects.filter(zones=zone, state=1).order_by('-id')
    if POI_CLASSES:
        resources = Poi.objects.filter(zones=zone, poitype_id__in=POI_CLASSES, state=1).order_by('-id')
    else:
        resources = Poi.objects.filter(zones=zone, state=1).order_by('-id')
    return resources
def resources_by_topo_count(zone):
    # n = Poi.objects.filter(zones=zone, state=1).count()
    if POI_CLASSES:
        n = Poi.objects.filter(zones=zone, poitype_id__in=POI_CLASSES, state=1).count()
    else:
        n = Poi.objects.filter(zones=zone, state=1).count()
    return n

@python_2_unicode_compatible
class PoiPoi(models.Model):
    from_poi = models.ForeignKey(Poi, models.CASCADE)
    to_poi = models.ForeignKey(Poi, models.CASCADE)
    # reltype_id = models.IntegerField('Tipo relazione', null=True, default=1)
    RELTYPE_CHOICES = (
        (1, 'risorsa affiliata a ..'),
        (2, 'servizio erogato da ..'),)
    reltype_id = models.IntegerField('Tipo relazione', choices=RELTYPE_CHOICES, default=1)

    class Meta:
        verbose_name = "relazione risorsa-risorsa"
        verbose_name_plural = "relazioni risorsa-risorsa"
        db_table = 'pois_poipoi'
        auto_created = Poi

    def __str__(self):
        return '%s: vedi %s' % (self.from_poi.getName(), self.to_poi.getName())

@python_2_unicode_compatible
class PoiMember(models.Model):
    poi = models.ForeignKey(Poi, models.CASCADE)
    member = models.ForeignKey(User, models.CASCADE)

    class Meta:
        verbose_name = "relazione risorsa-membro"
        verbose_name_plural = "relazioni risorsa-membri"
        db_table = 'pois_poimember'
        auto_created = Poi

    def __str__(self):
        return '%s in %s' % (self.member, self.poi.poi())
        
        
#MMR 180406
#risorse e categorie da visualizzare in Homepage
@python_2_unicode_compatible
class Confighome(models.Model):
    poi = models.ForeignKey(Poi, models.CASCADE, blank=True, null=True)
    poitype = models.ForeignKey(Poitype, models.CASCADE, blank=True, null=True)
    image = models.ImageField(upload_to='img_home', null=True, blank=True, verbose_name='immagine')
    order = models.IntegerField(verbose_name='posizione', default=0)
    view = models.BooleanField(verbose_name='mostra', default=False)
    created = models.DateTimeField(verbose_name='Creata il', auto_now_add=True, blank=True, null=True)
    modified = models.DateTimeField(verbose_name='Mod. il', auto_now=True, blank=True, null=True)
    class Meta:
        verbose_name = "configurazione homepage"
        verbose_name_plural = "configurazione homepage"
        db_table = 'pois_confighome'

"""
MMR temporaneamente disattivato
class Blog(models.Model):

    # Defines a blog

    title = models.CharField(verbose_name=_('Title'), max_length=255)
    author = models.ForeignKey(User, related_name='blog_author')
    slug = AutoSlugField(unique=True, populate_from='title', editable=True, blank=True, null=True)
    description = models.TextField(verbose_name=_('Description'), blank=True, null=True)   
    # aggiunto 130603
    host_type = models.ForeignKey(ContentType, verbose_name='Ospitato da (zona o risorsa)', null=True)
    host_id = models.PositiveIntegerField(blank=True, null=True)
    # MMR old version - host_object = generic.GenericForeignKey('host_type', 'host_id')
    host_object = GenericForeignKey('host_type', 'host_id')
    state = models.IntegerField(verbose_name='Stato', choices=STATE_CHOICES, default=0, null=True)

    def __unicode__(self):
        return self.title

    def link(self):
        # return '/blog/%d/posts' % self.id
        return '/blog/%d/' % self.id

    def get_author_name(self):
        return '%s %s' % (self.author.first_name, self.author.last_name)
        
    def get_host_name(self):
        # return self.content_object.name
        host = self.host_object
        if host:
            content_type = ContentType.objects.get_for_model(host)
            model = content_type.model_class()
            if model == Zone:
                return 'Zona %s' % host.name
            elif model == Poi:
                return host.prefixed_name()
            else:
                return host.name
        else:
            return ''

    def get_host(self):
        return self.host_object

    def posts(self):
        return Post.objects.filter(blog=self)

    def can_edit(self, request):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser or (user.is_staff and user==self.author):
            return True
        return False

    def can_post(self, request):
        user = request.user
        if not user.is_authenticated:
            return False
        if user==self.author:
            return True
        return False

    def friendly_url(self):
        return '/blog/%s/' % self.slug
"""
class ZonetypeTranslation(object):
    fields = ('name', 'name_plural')
register(Zonetype, ZonetypeTranslation)

class TagTranslation(object):
    fields = ('name','short')
register(Tag, TagTranslation)

class PoitypeTranslation(object):
    fields = ('name','short')
register(Poitype, PoitypeTranslation)

"""
MMR - temporaneamente disattivato

# Post.add_to_class('blog', models.ForeignKey(Blog, related_name='post_blog', editable=False))
Post.add_to_class('blog', models.ForeignKey(Blog, related_name='post_blog'))
def blog_id(self):
    return self.blog.id
blog_id.short_description = "Blogid"
Post.blog_id = blog_id

def blog_title(self):
    return self.blog.title
blog_title.short_description = "Blog"
Post.blog_title = blog_title

def post_can_edit(self, request):
    user = request.user
    if not user.is_authenticated:
        return False
    if user.is_superuser or user==self.author or user==self.blog.author:
        return True
    return False
Post.can_edit = post_can_edit
"""

def refresh_configuration():
    rebuild_poi_categories()
    rebuild_icon_map()

refresh_configuration()

POI_CLASSES = Poitype.objects.filter(slug__in=POITYPE_SLUGS).values_list('klass', flat=True)


