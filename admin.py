# from django.contrib import admin
from django.contrib.gis import admin
from django.contrib.gis.geos import Point
from tinymce.widgets import TinyMCE

from pois.models import Zonetype, Zone, ZoneZone, Route, Odonym, Tag, TagTag, Poitype, Sourcetype, Poi, PoiZone, PoiRoute, PoiPoi # MMR temporaneamente disattivato -, Blog
from pois.forms import ZoneForm, RouteForm, PoiForm  # MMR temporaneamente disattivato -, BlogForm

from roma.settings import srid_OSM
srid_GPS = 4326 # WGS84 = World Geodetic System 1984 (the reference system used by GPS)
# srid_OSM = 900913 # the Google Map's modified Mercator projection (default in PostGIS, used by OSM)
# srid_OSM = 3857 # the projection used by OSM, GMaps and Bing tile server
roma_lon = 12.4750
roma_lat = 41.9050
mazzini_lon = 12.463553
mazzini_lat = 41.915914

# vedi definizione di OSMGeoAdmin in modulo django.contrib.gis.admin.options
from django.contrib.gis.admin.options import GeoModelAdmin
from django.contrib.gis import gdal
"""
MMR temporaneamente disattivato - old version
if gdal.HAS_GDAL:
    # Use the official spherical mercator projection SRID on versions
    # of GDAL that support it; otherwise, fallback to 900913.
    if gdal.GDAL_VERSION >= (1, 7):
        spherical_mercator_srid = 3857
    else:
        spherical_mercator_srid = 900913

    class MultiGeoAdmin(GeoModelAdmin):
        map_template = 'admin/pois/multi.html'
        num_zoom = 20
        map_srid = spherical_mercator_srid
        max_extent = '-20037508,-20037508,20037508,20037508'
        max_resolution = '156543.0339'
        point_zoom = num_zoom - 6
        units = 'm'
"""
if gdal.GDAL_VERSION >= (1, 7):
    spherical_mercator_srid = 3857
else:
    spherical_mercator_srid = 900913

class MultiGeoAdmin(GeoModelAdmin):
     map_template = 'admin/pois/multi.html'
     num_zoom = 20
     map_srid = spherical_mercator_srid
     max_extent = '-20037508,-20037508,20037508,20037508'
     max_resolution = '156543.0339'
     point_zoom = num_zoom - 6
     units = 'm'

class PoiInLine(admin.TabularInline):
    model = Poi
    extra = 5

class ZonetypeAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['name', 'name_en', 'name_plural', 'name_plural_en', 'slug',]}),
    ]
    list_display = ('id', 'name', 'name_en', 'name_plural', 'name_plural_en', 'slug',)
    search_fields = ['name']

# class ZoneAdmin(admin.ModelAdmin):
# class ZoneAdmin(admin.GeoModelAdmin):
class ZoneAdmin(admin.OSMGeoAdmin):
    pnt = Point(roma_lon, roma_lat, srid=srid_GPS)
    pnt.transform(srid_OSM)
    default_lon, default_lat = pnt.coords
    default_zoom = 13
    form = ZoneForm
    fieldsets = [
        (None, {'fields': ['code', 'name', 'zonetype', 'pro_com', 'slug', 'short', 'description', 'zones', 'web',]}),
        ('Estensione', {'fields': ['geom',]}),
    ]
    list_display = ('id', 'code', 'name', 'zonetype', 'slug', 'modified', 'short', 'desc_len', 'careof_name',)
    search_fields = ['code', 'name',]
    # inlines = [PoiInLine]

    def careof_name(self, obj):
        careof = obj.careof
        if careof:
            return obj.careof.name
        else:
            return ''
    careof_name.short_description = 'A cura di'

    def desc_len(self, obj):
        description = obj.description
        return description and len(description) or ''
    desc_len.short_description = 'Car. descr.'

class ZoneZoneAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['from_zone', 'to_zone', 'overlap', 'distance',]}),
    ]
    list_display = ('from_zone', 'to_zone', 'overlap', 'distance',)
    search_fields = ['from_zone', 'to_zone',]

class RouteAdmin(admin.OSMGeoAdmin):
    pnt = Point(roma_lon, roma_lat, srid=srid_GPS)
    pnt.transform(srid_OSM)
    default_lon, default_lat = pnt.coords
    default_zoom = 13
    form = RouteForm
    fieldsets = [
        (None, {'fields': ['code', 'name', 'slug', 'short', 'description', 'web', 'state',]}),
        ('Estensione', {'fields': ['coords', 'geom',]}),
    ]
    list_display = ('id', 'code', 'name', 'slug', 'modified', 'short', 'desc_len',)
    search_fields = ['code', 'name',]

    def desc_len(self, obj):
        description = obj.description
        return description and len(description) or ''
    desc_len.short_description = 'Car. descr.'

class OdonymAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['name', 'slug', 'short', 'description', 'web',]}),
    ]
    list_display = ('id', 'name', 'slug', 'modified', 'short',)
    search_fields = ['name']

class TagAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['name_en', 'name', 'slug', 'weight', 'color', 'tags',]}),
    ]
    list_display = ('id', 'name_en', 'name', 'slug', 'modified', 'weight', 'color',)
    search_fields = ['name_en', 'name',]

class TagTagAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['from_tag', 'to_tag',]}),
    ]
    list_display = ('from_tag', 'to_tag',)
    search_fields = ['from_tag', 'to_tag',]

class PoitypeAdmin(admin.ModelAdmin):
    list_display = ('klass', 'name_en', 'name', 'slug', 'modified', 'active', 'list_themes', 'icon', 'color',)
    search_fields = ['name_en', 'name',]

    def list_themes(self, obj):
        tags = obj.tags.all()
        return ', '.join([tag.getName() for tag in tags])
    list_themes.short_description = 'Elenco temi'

class SourcetypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name',)

# class PoiAdmin(admin.ModelAdmin):
# class PoiAdmin(admin.GeoModelAdmin):
# class PoiAdmin(admin.OSMGeoAdmin):
class PoiAdmin(MultiGeoAdmin):
    pnt = Point(roma_lon, roma_lat, srid=srid_GPS)
    pnt.transform(srid_OSM)
    default_lon, default_lat = pnt.coords
    default_zoom = 13
    form = PoiForm
    # list_display = ('id', 'name', 'kind', 'category_short', 'list_themes', 'comune', 'zipcode', 'lat_long', 'street_name', 'housenumber', 'list_zones', 'short', 'list_web', 'state', 'N', 'careof_name', 'owner', 'lasteditor', 'modified',)
    list_display = ('id', 'name', 'category_short', 'list_themes', 'comune', 'zipcode', 'lat_long', 'get_street_address', 'list_zones', 'short', 'list_web', 'state', 'N', 'careof_name', 'owner', 'lasteditor', 'modified',)
    list_filter = ('poitype__name',)
    search_fields = ['name', 'description',]
    # inlines = [PoiInLine]

    def category_short(self, obj):
        if not obj.poitype:
            return ''
        name = obj.poitype.getName()
        if len(name) > 40:
            name = name[:36] + ' ...'
        return name
    category_short.short_description = 'Categoria'

    def comune(self, obj):
        """
        try:
            zone = Zone.objects.get(pro_com=obj.pro_com)
            return zone.name
        except:
            return 'Roma' # obj.pro_com
        """
        return obj.get_comune()

    """
    def street_name(self, obj):
        return obj.street_name()
    street_name.short_description = 'Via'
    """
    def get_street_address(self, obj):
        return obj.get_street_address()
    get_street_address.short_description = 'Indirizzo'

    def more_types(self, obj):
        moretypes = obj.moretypes.all()
        if moretypes:
            return ' '.join([poitype.getName() for poitype in moretypes])
        else:
            return ''
    more_types.short_description = 'Altre categorie'

    def list_themes(self, obj):
        themes = ', '.join([tag.getName() for tag in obj.get_themes_indirect()])
        # tags = obj.tags.all()
        tags = obj.get_themes()
        if tags:
            direct = ', '.join([tag.getName() for tag in tags])
            themes += ' + ' + direct
        return themes
    list_themes.short_description = 'Temi'

    def list_zones(self, obj):
        zones = obj.zones.all()
        return ', '.join([zone.zone() for zone in zones])
    list_zones.short_description = 'Zone'

    def list_web(self, obj):
        """
        web = obj.web
        if web:
            urls = web.split('\n')
        """
        web = ''
        urls = obj.safe_web()
        if urls:
            out = []
            for url in urls:
                if not url:
                    continue
                label = url
                if len(label) > 20:
                    label = label[:16] + '...'
                # link = '<a href="http://%s" target="_blank">%s</a>' % (url, label)
                link = '<a href="%s" target="_blank">%s</a>' % (url, label)
                out.append(link)
            web = ', '.join(out)
        return web
    list_web.short_description = 'Siti web'
    list_web.allow_tags = True

    def N(self, obj):
        # return obj.notes and '*' or ''
        notes = obj.notes and obj.notes.strip() or ''
        if notes:
            if notes[0] in ['\n', '\r']:
                return '**'
            else:
                return '*'
        else:
            return ''

    def careof_name(self, obj):
        careof = obj.careof
        if careof:
            return obj.careof.name
        else:
            return ''
    careof_name.short_description = 'A cura di'

    def save_model(self, request, obj, form, change):
        user = request.user
        obj.lasteditor = user
        if not obj.owner:
            obj.owner = user
        if not obj.careof:
            # orgs = Poi.objects.filter(members=user)
            orgs = Poi.objects.filter(members=obj.owner)
            if len(orgs)==1:
                obj.careof = orgs[0]
        obj.save()

    def queryset(self, request):
        qs = super(PoiAdmin, self).queryset(request)
        user = request.user
        if user.is_staff:
            return qs
        return qs.filter(owner=user)

class PoiZoneAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['poi', 'zone',]}),
    ]
    list_display = ('poi', 'zone',)
    search_fields = ['poi', 'zone',]

class PoiRouteAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['poi', 'route', 'order',]}),
    ]
    list_display = ('poi', 'route', 'order',)
    search_fields = ['poi', 'route',]

class PoiPoiAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['from_poi', 'to_poi', 'reltype_id']}),
    ]
    list_display = ('from_poi', 'to_poi', 'reltype_id',)
    search_fields = ['from_poi', 'to_poi',]

"""
MMR temporaneamente disattivato
class BlogAdmin(admin.ModelAdmin):
    form = BlogForm
    list_display = ('id', 'title', 'get_host_name', 'author', 'state', 'description',)
    search_fields = ['title',]
"""

admin.site.register(Zonetype, ZonetypeAdmin)
admin.site.register(Zone, ZoneAdmin)
admin.site.register(ZoneZone, ZoneZoneAdmin)
admin.site.register(Route, RouteAdmin)
admin.site.register(Odonym, OdonymAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(TagTag, TagTagAdmin)
admin.site.register(Poitype, PoitypeAdmin)
admin.site.register(Sourcetype, SourcetypeAdmin)
admin.site.register(Poi, PoiAdmin)
admin.site.register(PoiZone, PoiZoneAdmin)
admin.site.register(PoiRoute, PoiRouteAdmin)
admin.site.register(PoiPoi, PoiPoiAdmin)
"""
MMR temporaneamente disattivato
admin.site.register(Blog, BlogAdmin)

from richtext_blog.models import Post
from richtext_blog.admin import PostAdmin

list_display = list(PostAdmin.list_display)
PostAdmin.list_display = list_display[:1] + ['blog_id', 'blog_title'] + list_display[1:]
PostAdmin.list_filter = ['blog__title'] + list(PostAdmin.list_filter)
PostAdmin.fields = ['blog'] + list(PostAdmin.fields)
"""

# override metodo response_post_save_change di ModelAdmin in modulo admin.options
# l'idea, presa da from http://www.ibm.com/developerworks/library/os-django-admin/
# prevedeva di fare l'override del metodo change_view, ma non funzionava
from django.http import HttpResponseRedirect
def response_post_save_change(self, request, obj):
    """
    Figure out where to redirect after the 'Save' button has been pressed
    when editing an existing object.
    """
    print (obj.get_absolute_url())
    return HttpResponseRedirect(obj.get_absolute_url())
    
"""
MMR temporaneamente disattivato
PostAdmin.response_post_save_change = response_post_save_change
"""
