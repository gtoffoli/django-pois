# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import requests
# Add before admin.autodiscover() and any form import for that matter:
from collections import defaultdict
from urllib.parse import urlsplit
import json

from django.core.cache import caches
from django.template.defaultfilters import slugify
"""
MMR temporaneamente disattivato
import autocomplete_light
autocomplete_light.autodiscover()
"""
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.contrib.gis.shortcuts import render_to_kml
from django.contrib.gis.geos import Polygon, LinearRing
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.flatpages.models import FlatPage
from django.contrib.auth.decorators import login_required
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils import translation
from django.utils.translation import ugettext_lazy as _ 
from django_user_agents.utils import get_user_agent

from django.conf import settings
from roma.session import get_focus, set_focus, focus_set_category, focus_add_themes
from django.db.models.functions import Lower
from pois.models import Zonetype, Zone, Route, Odonym, Poitype, Poi, Tag, PoiPoi
from pois.models import list_all_zones
from pois.models import make_zone_subquery
from pois.models import refresh_configuration
from pois.forms import PoiUserForm, PoiAnnotationForm
from pois.models import MACROZONE, TOPOZONE, MUNICIPIO, CAPZONE
from pois.forms import  PoiBythemeForm, PoiSearchForm
from pois.models import POI_CLASSES

from roma.settings import LANGUAGE_CODE
from roma.settings import MAX_POIS

from roma.settings import srid_OSM
srid_GPS = 4326 # WGS84 = World Geodetic System 1984 (the reference system used by GPS)
# srid_OSM = 900913 # the Google Map's modified Mercator projection (default in PostGIS, used by OSM)
srid_ISTAT = 23032
roma_lon = 12.4750
roma_lat = 41.9050
from django.contrib.gis import admin
from django.contrib.gis.geos import Point

from dal import autocomplete

class ZoneAdmin(admin.OSMGeoAdmin):
    pnt = Point(roma_lon, roma_lat, srid=srid_GPS)
    pnt.transform(srid_OSM)
    default_lon, default_lat = pnt.coords
    default_zoom = 13
    list_filter = ('geom',)
    list_display = ('geom',)

def zonetype_index(request):
    if request.user.is_superuser or request.user.is_staff:
        zonetypes = [Zonetype.objects.get(pk=id) for id in [0,7,1,3,4,5,6]]
        zonetype_list = []
        for zt in zonetypes:
            zonetype_list.append([zt, zt.name, Zone.objects.filter(zonetype=zt.pk).count()])
        return render(request, 'pois/pois_report/zonetype_index.html', {'zonetype_list': zonetype_list,})
    return HttpResponseRedirect('/')

def zonetype_detail(request, zonetype_id, zonetype=None):
    if request.user.is_superuser or request.user.is_staff:
        if not zonetype:
            zonetype = get_object_or_404(Zonetype, pk=zonetype_id)
        zonetype_name = zonetype.name
        zone_list = Zone.objects.filter(zonetype=zonetype_id).exclude(id=90).order_by('id')
        return render(request,'pois/pois_report/zonetype_detail.html', {'zonetype': zonetype, 'zonetype_name': zonetype_name, 'zone_list': zone_list,})
    return HttpResponseRedirect('/')
    
def zonetype_detail_by_slug(request, zonetype_slug):
    zonetype = get_object_or_404(Zonetype, slug=zonetype_slug)
    return zonetype_detail(request, zonetype.id, zonetype)

@xframe_options_exempt
def zone_index(request, zonetype_id=None):
    if zonetype_id:
        zonetype = get_object_or_404(Zonetype, pk=zonetype_id)
        zonetype_name = zonetype.name
        zone_list = Zone.objects.filter(zonetype=zonetype_id).exclude(id=90).order_by('id')
    else:
        zonetype = None
        zonetype_name = ''
        zone_list = Zone.objects.filter(zonetype_id__in=[0,7,3,6]).exclude(id=90).order_by('zonetype__name', 'id')
    return render(request, 'pois/zone_index.html', {'zonetype': zonetype, 'zonetype_name': zonetype_name, 'zone_list': zone_list,})

def zone_index_map(request, zonetype_id=1, prefix='', render_view=True):
    zonetype = get_object_or_404(Zonetype, pk=zonetype_id)
    zonetype_label = zonetype_short = ''
    region = 'LAZIO'
    user_agent = get_user_agent(request)
    view_map = user_agent.is_pc or user_agent.is_tablet
    if zonetype_id or zonetype_id==0:
        if zonetype_id==0 and prefix:
            zone_list = Zone.objects.filter(zonetype=zonetype_id, code__istartswith=prefix).exclude(geom__isnull=True).order_by('name')
            zonetype_label = prefix=='RM.' and ('%s %s' %(_('macrozones'),_('of Roma'))) or prefix=='PR.' and ('%s %s' %(_('provinces'),_('of Lazio')))
            zonetype_short = prefix=='RM.' and _('map of the macrozones of Roma') or prefix=='PR.' and _('map of the provinces of Lazio')
            region = prefix=='RM.' and 'ROMA' or prefix=='PR.' and 'LAZIO'
        elif zonetype_id==3 and prefix:
            zone_list = Zone.objects.filter(zonetype=zonetype_id, code__istartswith=prefix).exclude(geom__isnull=True).order_by('name')
            if prefix=='Z.':
                 zonetype_label = _('suburban zones')
                 zonetype_short = _('map of the suburban zones')
            else:
                zonetype_label = prefix=='R.' and _('historical quarters') or prefix=='Q.' and _('quarters') or prefix=='S.' and _('quarter extensions')
                zonetype_label += ' %s' % _('of Roma')
                zonetype_short = prefix=='R.' and _('map of the historical quarters of Roma') or prefix=='Q.' and _('map of the quarters of Roma') or prefix=='S.' and _('map of the quarter extensions of Roma')
            region = 'ROMA'
        elif zonetype_id==7 and prefix:
            zone_list = Zone.objects.filter(zonetype=zonetype_id, code__istartswith=prefix).exclude(geom__isnull=True)
            zonetype_label = prefix=='M.' and ('%s %s' %(_('municipalities'),_('of Roma'))) or prefix=='COM.' and ('%s %s' %_('towns',_('of Lazio')))
            zonetype_short = prefix=='M.' and _('map of the municipalities of Roma') or prefix=='COM.' and _('map of the towns of Lazio')
            region = prefix=='M.' and 'ROMA' or prefix=='COM.' and 'LAZIO'
        else:
            zone_list = Zone.objects.filter(zonetype=zonetype_id).exclude(geom__isnull=True)
            if zonetype_id==0:
                zone_list = zone_list.exclude(code='ROMA')
                zonetype_label = _('macrozones')
                region = 'ROMA / LAZIO'
            elif zonetype_id==6:
                zonetype_label = _("zipcode areas")
                region = 'ROMA / LAZIO'
            elif zonetype_id==3:
                zonetype_label = _("traditional city districts")
                region = 'ROMA'
            else:
                zonetype_label = Zonetype.objects.get(pk=zonetype_id).name
    else:
        zone_list = Zone.objects.all()
    zcount = zone_list.count()
    zone_list = [zone.make_dict() for zone in zone_list]
    if zonetype_short:
        zonetype_short += '. %s' % _('Find easily useful facilities and services in the area that interests you. Schools, social and health services, cultural resources and much more.')
    data_dict = {'view_map': view_map, 'zonetype': zonetype, 'zone_list' : zone_list, 'zone_count' : zcount, 'zonetype_label': zonetype_label, 'zonetype_short': zonetype_short, 'region': region, 'prefix': prefix}

    if render_view:
       return render(request, 'pois/zone_index_map.html', data_dict)
    else:
        return data_dict
 
def zone_kml(request, zonetype_id=6):
    if zonetype_id:
        zone_list = Zone.objects.filter(zonetype=zonetype_id)
    else:
        zone_list = Zone.objects.all()
    return render_to_kml("zones.kml", {'zones' : zone_list}) 

"""
def muoviroma(request):
    flatpage = FlatPage.objects.get(url='/help/muoviroma/')
    text_body = flatpage.content
    return render(request, 'pois/muoviroma.html', {'text_body': text_body})
"""

def tag_set(request, tag_id, redirect=True):
    set_focus(request, tags=[tag_id])
    if redirect:
        referer = request.META.get('HTTP_REFERER', None)
        redirect_to = urlsplit(referer, 'http', False)[2]
        return HttpResponseRedirect(redirect_to)

def tag_toggle(request, tag_id, redirect=True):
    focus = get_focus(request)
    tags = focus.get('tags', [])
    """
    MMR 20181701
    print ('TAG_TOGGLE')
    print ('tag_id: ', tag_id)
    print ('focus: ', focus)
    print ('tags: ', tags)
    """
    if tag_id in tags:
        tags.remove(tag_id)
    else:
        tags.append(tag_id)
    set_focus(request, tags=tags)
    """
    MMR 20181701
    print ('focus: ', get_focus(request))
    print ('tags: ', tags)
    """
    if redirect:
        referer = request.META.get('HTTP_REFERER', None)
        redirect_to = urlsplit(referer, 'http', False)[2]
        return HttpResponseRedirect(redirect_to)

# compute parameters for zone_map.html and render it or just return data
def zone_map(request, zone_id, render_view=True, zone=None):
    if not zone:
        zone = get_object_or_404(Zone, pk=zone_id)
        if render_view:
            return HttpResponseRedirect('/zona/%s/' % zone.slug)
    set_focus(request, zones=[int(zone_id)])

    can_edit = zone.can_edit(request)
    # calcola filtro per zona e filtra le risorse con esso
    macrozones = []
    subzone_list = []
    q = make_zone_subquery(zone)
    if zone.zonetype_id == MACROZONE:
        subzone_list = zone.list_subzones(zonetype_id=TOPOZONE)
    elif zone.zonetype_id in [TOPOZONE, MUNICIPIO]:
        macrozones = Zone.objects.filter(zonetype_id=MACROZONE, zones=zone)
    poi_list = Poi.objects.filter(q & Q(state=1))
    poitype_ids = poi_list.values_list('poitype_id', flat=True).distinct()
    region = "ROMA"
    if zone.code.startswith('PR') or zone.code.startswith('COM'):
        region="LAZIO"
    # compute categories (poitypes) and themes (tags) for all resources in region
    poitypes = Poitype.objects.filter(klass__in=poitype_ids).order_by('klass')
    tags = Tag.objects.filter(Q(poitype__in=poitypes) | Q(poi__in=poi_list)).exclude(id=49).distinct() # 130729 esteso: OK

    focus = get_focus(request)
    focus_tag_ids = focus.get('tags', [])

    # finalize the tag list
    tag_list = []
    selected_tag = None
    tag_ids = [tag.id for tag in tags]
    for tag_id in focus_tag_ids:
        if not selected_tag and tag_id in tag_ids:
            selected_tag = tag_id
    if tag_ids and not selected_tag:
        selected_tag = tag_ids[0]
        set_focus(request, tags=[selected_tag])
    for tag in tags:
        tag_list.append([tag.id, tag.name, tag.id==selected_tag and 'bold' or '',])

    # re-compute poitypes, based also on selected_tag ?
    if selected_tag:
        klasses = poitypes.filter(tags=selected_tag).values_list('klass', flat=True).distinct()
        focused_poi_klasses = poi_list.filter(tags=selected_tag).values_list('poitype_id', flat=True).distinct()
        if focused_poi_klasses:
            klasses = list(klasses)
            klasses.extend(focused_poi_klasses)
            klasses = list(set(klasses))
        poitypes = Poitype.objects.filter(klass__in=klasses).order_by('klass')
        poitype_ids = [poitype.id for poitype in poitypes]
    else:
        poitypes = []
        poitype_ids = []

    # compute a dict, then an ordered list, of resources by poitype
    poitype_dict = defaultdict(list)
    for poitype in poitypes:
        poitype_dict[poitype.id] = [poitype]
    poitype_list = [[key, poitype_dict[key]] for key in poitype_ids]
    data_dict = {'zone': zone, 'macrozones': macrozones, 'subzone_list': subzone_list, 'tag_list': tag_list, 'tag_id': selected_tag, 'poitype_list': poitype_list, 'region': region, 'can_edit': can_edit,}
    if render_view:
        flatpage = FlatPage.objects.get(url='/help/zonemap/')
        data_dict['help'] = flatpage.content
        return render(request, 'pois/zone_map.html', data_dict)
    else:
        return data_dict

def zone_map_by_slug(request, zone_slug):
    zone = get_object_or_404(Zone, slug=zone_slug)
    theme = request.GET.get('tema', None)
    if theme:
        tag = Tag.objects.get(slug=theme)
        set_focus(request, tags=[tag.id])
    category_slug = request.GET.get('categoria', None)
    if category_slug:
        category = Poitype.objects.get(slug=category_slug)
        focus_set_category(request, category.klass)
        if not theme:
            tags = category.tags.all()
            if tags:
                set_focus(request, tags=[tags[0].id])
    return zone_map(request, zone.id, zone=zone)

# compute the resources for the given zone and category
def zone_type_resources(request, zone_id, poitype):
    focus = get_focus(request)
    focus_tag_ids = focus.get('tags', [])
    zone = get_object_or_404(Zone, pk=zone_id)
    q = make_zone_subquery(zone)
    return resources_by_tags_and_type(focus_tag_ids, poitype.klass, q=q)

# chiamata da zone_map.html, direttamente (caricamento pagina) tramite url zone_themes
# o, indirettamente (azione di utente), tramite url zone_toggle_theme o zone_set_theme
def zone_themes(request, tag_id=None):
    zone_ids = get_focus(request).get('zones', [])
    if zone_ids:
        zone_id = zone_ids[0]
    else:
        zone_id = 91
    data_dict = zone_map(request, zone_id, render_view=False)
    tag_list = data_dict['tag_list']
    poitype_list = data_dict['poitype_list']
    poitype_dict_list = []
    klass_list = []
    for item in poitype_list:
        poitype_dict = {}
        poitype_dict['id'] = item[0]
        objects = item[1]
        poitype = objects[0]
        poitype_dict['name'] =  poitype.name
        poitype_dict['klass'] =  poitype.klass
        klass_list.append(poitype_dict['klass'])
        poitype_dict['icon'] =  poitype.icon_name()
        pois = objects[1:]
        # poi_list = [poi.make_dict() for poi in pois]
        poi_list = [poi.make_dict(list_item=True) for poi in pois]
        poitype_dict['pois'] = poi_list
        poitype_dict_list.append(poitype_dict)
    # sceglie la categoria da visualizzare dopo load pagina o modifica temi
    klass = ''
    if poitype_dict_list:
        klass = poitype_dict_list[0]['klass']
    if not tag_id: # caricamento pagina
        klasses = get_focus(request).get('klasses', [])
        for j in reversed(range(len(klasses))):
            if klasses[j] in klass_list:
                klass = klasses[j]
                break
    if klass_list and not klass:
        klass = klass_list[0]
    json_data = json.dumps({'HTTPRESPONSE': 1, 'theme_list': tag_list, 'resource_list': poitype_dict_list, 'category': klass})
    return HttpResponse(json_data, content_type="application/x-json")

def zone_set_theme(request, tag_id):
    tag_id = int(tag_id)
    tag_set(request, tag_id, redirect=False)
    return zone_themes(request, tag_id=tag_id)

# called by zone_map.html to notify click on theme button
def zone_toggle_theme(request, tag_id):
    tag_id = int(tag_id)
    tag_toggle(request, tag_id, redirect=False)
    return zone_themes(request, tag_id=tag_id)

# called by zone_map.html to notify click on resource category button
def zone_set_category(request, klass):
    zone_ids = get_focus(request).get('zones', [])
    if zone_ids:
        zone_id = zone_ids[0]
    else:
        zone_id = 91
    poitype = Poitype.objects.get(klass=klass)
    # remember last klass selected
    focus_set_category(request, klass)
    pois = zone_type_resources(request, zone_id, poitype)
    # poi_list = [poi.make_dict() for poi in pois]
    poi_list = [poi.make_dict(list_item=True) for poi in pois]
    json_data = json.dumps({'HTTPRESPONSE': 1, 'resource_list': poi_list,})
    # return HttpResponse(json_data, mimetype="application/json")
    return HttpResponse(json_data, content_type="application/x-json")

@xframe_options_exempt
def street_detail(request, street_id, street=None):
    if not street:
        street = get_object_or_404(Odonym, pk=street_id)
        return HttpResponseRedirect('/toponimo/%s/' % street.slug)
    language = translation.get_language() or 'en'
    streets_cache = caches['streets']
    key = 'street_%05d' % street_id
    if not language.startswith('it') or request.GET.get('nocache', None):
        data_dict = None
    else:
        data_dict = streets_cache.get(key, None)
    if data_dict:
        print ('%s valid' % key)
    else:
        print ('%s invalid' % key)
        help_text = FlatPage.objects.get(url='/help/street/').content
        zones = street.get_zones()
        zone_list = [zone.make_dict(list_item=True) for zone in zones[0]]
        zone_zipcode_list = [zone.make_dict(list_item=True) for zone in zones[1]]
        pois = Poi.objects.select_related().filter(street=street, state=1)
        if POI_CLASSES:
            pois = pois.filter(poitype_id__in=POI_CLASSES)
        pois = pois.order_by('name')
        poi_dict_list_no_sorted = [poi.make_dict(list_item=True) for poi in pois]
        poi_dict_list = sorted(poi_dict_list_no_sorted, key=lambda k: k['name'].lower())
        region = 'ROMA'
        if poi_dict_list:
            for item in poi_dict_list:
                if item['comune'][1] != 'roma':
                    region = 'LAZIO' 
                    break
        data_dict = {'help': help_text, 'street_name': street.name, 'street_id': street.id, 'zone_list': zone_list, 'zone_zipcode_list': zone_zipcode_list, 'poi_dict_list': poi_dict_list, 'view_type': 'street', 'region': region}
        if language.startswith('it'):
            try:
                streets_cache.set(key, data_dict)
            except:
                """
                MMR 20181701
                print (data_dict)
                """
                pass
    can_edit = street.can_edit(request)
    data_dict['can_edit'] = can_edit
    return render(request, 'pois/street_detail.html', data_dict)

def street_detail_by_slug(request, street_slug):
    street = get_object_or_404(Odonym, slug=street_slug)
    return street_detail(request, street.id, street)

@xframe_options_exempt
def zone_detail(request, zone_id, zone=None):
    if not zone:
        zone = get_object_or_404(Zone, pk=zone_id)
        return HttpResponseRedirect('/zona/%s/' % zone.slug)
    language = translation.get_language() or 'en'
    zonemaps_cache = caches['zonemaps']
    key = 'zone%04d' % zone_id
    if not language.startswith('it') or request.GET.get('nocache', None):
        data_dict = None
    else:
        data_dict = zonemaps_cache.get(key, None)
    if data_dict:
        print ('%s valid' % key)
    else:
        print ('%s invalid' % key)
        help_text = FlatPage.objects.get(url='/help/zone/').content.replace('</p>', '')
        macrozones = []
        subzone_list = []
        zone_dict = zone.make_dict()
        zone_dict['prefix'] = zone.zone_parent()
        zone_dict['type_subzones'] = [z.make_dict(list_item=True) for z in zone.type_subzones()]
        zone_dict['sametype_zones'] = [z.make_dict(list_item=True) for z in zone.sametype_zones()]
        zone_dict['neighbouring'] = zone.neighbouring()
        """
        MMR 20181701
        overlapping rimosso
        zone_dict['overlapping'] = [z.make_dict(list_item=True) for z in zone.overlapping()]
        """
        if zone.zonetype_id == MACROZONE:
            subzone_list = zone.list_subzones(zonetype_id=TOPOZONE)
        elif zone.zonetype_id in [TOPOZONE, MUNICIPIO]:
            macrozones = Zone.objects.filter(zonetype_id=MACROZONE, zones=zone)
            macrozones = [z.make_dict for z in macrozones]
        # VEDI def make_zone_subquery(zone): in models.py
        if zone.zonetype_id == CAPZONE:
            pois = Poi.objects.select_related().filter(zipcode=zone.code, state=1) # .order_by('name')
        elif zone.zonetype_id == MACROZONE:
            subzones = zone.zones.filter(zonetype_id=MUNICIPIO)
            zone_ids = [subzone.id for subzone in subzones]
            pois = Poi.objects.select_related().filter(zones__in=zone_ids, state=1) # .order_by('name')
        else:
            pois = Poi.objects.select_related().filter(zones=zone, state=1) # .order_by('name')
        if POI_CLASSES:
            pois = pois.filter(poitype_id__in=POI_CLASSES)
        pois = pois.order_by('name')
        poi_dict_list_no_sorted = [poi.make_dict(list_item=True) for poi in pois]
        poi_dict_list = sorted(poi_dict_list_no_sorted, key=lambda k: k['name'].lower())
        form = PoiBythemeForm()
        data_dict = {'help': help_text, 'zone': zone_dict, 'macrozones': macrozones, 'subzone_list': subzone_list, 'poi_dict_list': poi_dict_list, 'form': form}
        if language.startswith('it'):
            try:
                zonemaps_cache.set(key, data_dict)
            except:
                """
                MMR 20181701
                print (data_dict)
                """
                pass
    data_dict['can_edit'] = zone.can_edit(request)
    return render(request, 'pois/zone_detail.html', data_dict)

def zone_detail_by_slug(request, zone_slug):
    zone = get_object_or_404(Zone, slug=zone_slug)
    return zone_detail(request, zone.id, zone)

def route_index(request):
    user = request.user
    if user.is_superuser or user.is_staff:
        routes = Route.objects.all()
        return render(request, 'pois/pois_report/route_index.html', {'routes': routes,})
    return HttpResponseRedirect('/')

@xframe_options_exempt
def route_detail(request, route_id, route=None):
    user = request.user
    if user.is_superuser or user.is_staff:
        if not route:
            route = get_object_or_404(Route, pk=route_id)
        data_dict = {}
        can_edit = route.can_edit(request)
        data_dict['can_edit'] = can_edit
        route_dict = route.make_dict()
        data_dict['route'] = route_dict
        pois = route.pois.all()
        poi_dict_list = [poi.make_dict(list_item=True) for poi in pois]
        data_dict['poi_dict_list'] = poi_dict_list
        near_pois = route.get_near_pois(distance=50)
        near_poi_dict_list = [poi.make_dict(list_item=True) for poi in near_pois if not poi in pois]
        data_dict['near_poi_dict_list'] = near_poi_dict_list
        return render(request, 'pois/pois_report/route_detail.html', data_dict)
    return HttpResponseRedirect('/')

def route_detail_by_slug(request, route_slug):
    route = get_object_or_404(Route, slug=route_slug)
    return route_detail(request, route.id, route)

@xframe_options_exempt
def viewport(request):
    help_text = FlatPage.objects.get(url='/help/viewport/').content
    focus = get_focus(request)
    tags = []
    if request.method == 'POST':
        tags = request.POST.getlist('tags')
    viewport = focus.get('viewport', None)
    if not viewport:
        try:
            w = float(request.GET['left'])
            s = float(request.GET['bottom'])
            e = float(request.GET['right'])
            n = float(request.GET['top'])
        except:
            return render(request, "roma/slim.html", {'text': '',})
        viewport = [w, s, e, n]
    pois = viewport_get_pois(request, viewport, tags=tags)
    if POI_CLASSES:
       pois = pois.filter(poitype_id__in=POI_CLASSES)
    pois = pois.order_by('name')
    poi_dict_list_no_sorted = [poi.make_dict(list_item=True) for poi in pois]
    poi_dict_list = sorted(poi_dict_list_no_sorted, key=lambda k: k['name'].lower())
    region = 'ROMA'
    if poi_dict_list:
        for item in poi_dict_list:
            if item['comune'][1] != 'roma':
                region = 'LAZIO' 
                break
    form = PoiBythemeForm(initial={'tags': tags})
    return render(request, 'pois/street_detail.html', {'help': help_text, 'poi_dict_list': poi_dict_list, 'view_type': 'viewport', 'form': form, 'tags': tags, 'region': region})

def zone_cloud(request):
    """ allows to test zone_cloud.html and zone_net """
    code = request.REQUEST['zone']
    zone = Zone.objects.filter(code=code)[0]
    return render(request, 'pois/zone_cloud.html', {'zone': zone})

zonetype_color_dict = {
   1: 'black',
   2: 'green',
   3: 'green',
   6: 'blue',
}
zonetype_importance_dict = {
   1: 2,
   2: 2,
   3: 2,
   6: 1,
}
zonetype_factor_dict = {
   1: 1,
   2: 1.3,
   3: 1.3,
   6: 1.6,
}
zonetype_name_dict = {
   1: 'code',
   2: 'name',
   3: 'name',
   6: 'code',
}
# from django.utils import simplejson
try:
    from django.utils import simplejson
except:
    simplejson = json

def zone_net(request):
    """ called by javascript handler in zonecloud.html """
    zone_id = int(request.REQUEST['zone_id'])
    width = float(request.REQUEST['width'])
    height = float(request.REQUEST['height'])
    soglia_1 = 5000
    soglia_2 = 5000
    from_zone = get_object_or_404(Zone, pk=zone_id)
    from_zonetype = from_zone.zonetype.id
    color = zonetype_color_dict[from_zonetype]
    zone_dict = {}
    centroids = []
    # costruisce la lista dei nodi e deg
    name = getattr(from_zone, zonetype_name_dict[from_zonetype])
    centroid = from_zone.geom.centroid
    centroids.append(centroid)
    x0 = centroid.x
    y0 = centroid.y
    min_x = max_x = x0
    min_y = max_y = y0
    node = { 'id': zone_id, 'name': name, 'importance': 3, 'color': 'red', 'group': 1, 'x': x0, 'y': y0, 'fixed': True, 'zonetype': from_zonetype }
    nodes = [node]
    i = 0
    zone_dict[zone_id] = i
    links = []
    zones = from_zone.get_neighbours(max_distance=1)
    for zone in zones:
        i += 1
        centroid = zone.geom.centroid
        x = centroid.x
        y = centroid.y
        """
        MMR 20181701
        print (x, y)
        """
        min_x = min(x, min_x)
        max_x = max(x, max_x)
        min_y = min(y, min_y)
        max_y = max (y, max_y)
        zonetype = zone.zonetype.id
        name = getattr(zone, zonetype_name_dict[zonetype])
        importance = zonetype_importance_dict[zonetype]
        color = zonetype_color_dict[zonetype]
        node = { 'id': zone.id, 'name': name, 'importance': importance, 'color': color, 'group': 1, 'x': x, 'y': y, 'fixed': True, 'zonetype': zonetype }
        nodes.append(node)
        centroids.append(centroid)
        zone_dict[zone.id] = i
        link = { 'source': 0, 'target': i, 'value': 1,}
        links.append(link)
    zones_1 = zones[:]
    zones.append(from_zone)
    # if from_zonetype != 1:
    if True:
        for zone_1 in zones_1:
            zonetype = zone.zonetype.id
            if zonetype in [1]:
                continue
            centroid = centroids[zone_dict[zone_1.id]]
            x = centroid.x
            y = centroid.y
            if x < min_x+soglia_1 or x>max_x-soglia_1 or y < min_y+soglia_1 or y>max_y-soglia_1:
                continue
            # more_zones = zone_1.get_neighbours(max_distance=1, zonetype=1)
            more_zones = zone_1.get_neighbours(max_distance=1)
            for zone in more_zones:
                if zone in zones:
                    continue
                zones.append(zone)
                centroid = zone.geom.centroid
                x = centroid.x
                y = centroid.y
                zonetype = zone.zonetype.id
                if x<min_x:
                    if min_x-x>soglia_2 or zonetype!=1:
                        continue
                    else:
                        x = min_x
                if y<min_y:
                    if min_y-y>soglia_2 or zonetype!=1:
                        continue
                    else:
                        y = min_y
                if x>max_x:
                    if x-max_x>soglia_2 or zonetype!=1:
                        continue
                    else:
                        x = max_x
                if y>max_y:
                    if y-max_y>soglia_2 or zonetype!=1:
                        continue
                    else:
                        y = max_y
                i += 1
                zonetype = zone.zonetype.id
                name = getattr(zone, zonetype_name_dict[zonetype])
                color = zonetype_color_dict[zonetype]
                importance = zonetype_importance_dict[zonetype]
                node = { 'id': zone.id, 'name': name, 'importance': min(importance, 2), 'color': color, 'group': 1, 'x': x, 'y': y, 'fixed': True, 'zonetype': zonetype, 'url': 'http://www.linkroma.it' }
                nodes.append(node)
                """
                zone_dict[zone.id] = i
                link = { 'source': zone_dict[zone_1.id], 'target': i, 'value': 1,}
                links.append(link)
                """
    # compute the scale factors
    fx = width / (max_x - min_x)
    fy = height / (max_y - min_y)
    # compute the start position as a linear combination of start projection and center of area
    node = nodes[0]
    dx = (node['x'] - min_x)
    x = dx * fx
    dy = (node['y'] - min_y)
    y = height - (dy * fy)
    a = 0.5
    b = 0.5
    cx = a*x + b*width/2
    cy = a*y + b*height/2
    nodes[0]['x'] = cx
    nodes[0]['y'] = cy
    for node in nodes[1:]:
        factor = zonetype_factor_dict[node['zonetype']]
        dx = (node['x'] - x0)
        x = cx + dx * fx * factor
        node['x'] = int(x)
        dy = (node['y'] - y0)
        y = cy - dy * fy * factor
        node['y'] = int(y)
    zone_dict = { 'nodes': nodes, 'links': links, }
    """
    MMR 20181701
    print (nodes)
    """
    resp = simplejson.dumps(zone_dict)
    return HttpResponse(resp, content_type='application/json')

def query_categories_by_tags(tag_ids):
    return Q(tags__in=tag_ids)

def query_resources_by_tags(tag_ids):
    return Q(tags__id__in=tag_ids) | Q(poitype__tags__in=tag_ids)

def resources_by_tags(tag_ids, q=None):
    """ riporta le risorse taggate direttamente, o indirettamente attraverso la categoria;
        consente di filtrare le risorse mediante una condizione aggiuntiva """
    state_query = Q(state=1)
    # tags_query = Q(tags__id__in=tag_ids) | Q(poitype__tags__in=tag_ids)
    tags_query = query_resources_by_tags(tag_ids)
    if q:
        pois = Poi.objects.filter(q & tags_query & state_query).distinct()
    else:
        pois = Poi.objects.filter(tags_query & state_query).distinct()
    return pois

def resources_by_tags_and_type(in_tag_ids, in_klass, q=None, count_only=False):
    """ riporta le risorse taggate direttamente, o indirettamente attraverso la categoria;
        consente di filtrare le risorse mediante una condizione aggiuntiva """
    tag_ids = Tag.objects.filter(poitype__klass=in_klass).exclude(id=49).values_list('id', flat=True)
    tag_intersection = set(tag_ids) & set(in_tag_ids)
    if tag_intersection:
        if q:
            pois = Poi.objects.filter(q & Q(poitype_id=in_klass, state=1)).distinct()
        else:
            pois = Poi.objects.filter(poitype_id=in_klass, state=1).distinct()
    else:
        if q:
            pois = Poi.objects.filter(q & Q(poitype_id=in_klass, state=1, tags__id__in=in_tag_ids)).distinct()
        else:
            pois = Poi.objects.filter(poitype_id=in_klass, state=1, tags__id__in=in_tag_ids).distinct()
    if count_only:
        count = pois.count()
        poi = count and pois[0] or None
        return count, poi
    else:
        return pois

def resources_by_tag_and_zone(tag, zone=None, list_all=False):
    poitype_klasses = Poitype.objects.filter(tags=tag).values_list('klass', flat=True)
    if zone:
        q = make_zone_subquery(zone)
        tag_poitype_klasses = Poi.objects.filter(Q(tags=tag, state=1) & q).values_list('poitype_id', flat=True).distinct()
    else:
        q = None
        tag_poitype_klasses = Poi.objects.filter(tags=tag, state=1).values_list('poitype_id', flat=True).distinct()
    klasses = list(set(poitype_klasses) | set(tag_poitype_klasses))
    if POI_CLASSES:
        klasses = [klass for klass in klasses if klass in POI_CLASSES]
    klasses.sort()
    m = len(klasses)
    poitypes = Poitype.objects.filter(klass__in=klasses).order_by('name')
    if not m:
        return 0, []
    n_pois = 0
    poitype_instances_list = []
    for poitype in poitypes:
        n, poi = resources_by_tags_and_type([tag.id], poitype.klass, q=q, count_only=True)
        if n or list_all:
            prefix = list_all and poitype.klass or ''
            # poitype_name = poitype.name
            poitype_tag_ids = poitype.tags.all().values_list('id', flat=True)
            category_in_theme = tag.id in poitype_tag_ids
            poi_url = n and poi.friendly_url() or ''
            # poitype_instances_list.append([prefix, poitype.slug, poitype.name, poitype.icon, n, category_in_theme, poi_url])
            poitype_instances_list.append([prefix, poitype.slug, poitype.name, poitype.get_icon(), n, category_in_theme, poi_url])
            n_pois += n
    return n_pois, poitype_instances_list

def resources_by_category_and_zone(klass, zone, select_related=False):
    q = make_zone_subquery(zone)
    poitype = Poitype.objects.filter(klass=klass)[0]
    if poitype.active:
        if select_related:
            resources = Poi.objects.select_related().filter(q & Q(poitype_id=klass, state=1)).order_by('name')
        else:
            resources = Poi.objects.filter(q & Q(poitype_id=klass, state=1)).order_by('name')
    else:
        klasses = poitype.sub_types(return_klasses=True)
        if select_related:
            resources = Poi.objects.select_related().filter(q & Q(poitype_id__in=klasses, state=1)).order_by('name')
        else:
            resources = Poi.objects.filter(q & Q(poitype_id__in=klasses, state=1)).order_by('name')
    return resources

@xframe_options_exempt
def tag_index(request):
    list_all = request.GET.get('all', None) is not None
    if list_all:
        refresh_configuration()
    tag_list = Tag.objects.all().exclude(id=49).order_by('weight')
    tag_poitype_list = []
    for tag in tag_list:
        tag_id = tag.id
        tag_name = tag.name
        tag_slug = tag.slug
        tag_url = tag.friendly_url
        n_pois, poitype_instances_list = resources_by_tag_and_zone(tag, list_all=list_all)
        if n_pois or list_all:
            tag_poitype_list.append([tag_id, tag_url, tag_name, tag_slug, n_pois, poitype_instances_list])
    return render(request, 'pois/tag_index.html', {'tag_poitype_list': tag_poitype_list})

@xframe_options_exempt
def zone_tag_index(request, zone_id, zone=None):
    if not zone:
        zone = get_object_or_404(Zone, pk=zone_id)
    language = translation.get_language() or 'en'
    zones_cache = caches['zones']
    key = 'zone%04d' % zone_id
    if not language.startswith('it') or request.GET.get('nocache', None):
        tag_poitype_list = None
        print ('%s invalid' % key)
    else:
        tag_poitype_list = zones_cache.get(key, None)
        print ('%s valid' % key)
    tag_poitype_list = None
    if not tag_poitype_list:
        tag_list = Tag.objects.all().exclude(id=49).order_by('weight')
        tag_poitype_list = []
        for tag in tag_list:
            n_pois, poitype_instances_list = resources_by_tag_and_zone(tag, zone=zone, list_all=False)
            if n_pois:
                # tag_poitype_list.append([tag, tag_name, tag_slug, n_pois, poitype_instances_list])
                tag_poitype_list.append([tag.id, tag.friendly_url(), tag.name, tag.slug, n_pois, poitype_instances_list])
        if language.startswith('it'):
            try:
                zones_cache.set(key, tag_poitype_list)
            except:
                """
                MMR 20181701
                print (tag_poitype_list)
                """
                pass
    cache = caches['custom']
    key = 'allzones_' + language
    if request.GET.get('nocache', None):
        all_zones = None
        print ('allzones invalid')
    else:
        all_zones = cache.set(key, None)
        print ('allzones valid')
    all_zones = None
    if not all_zones:
        all_zones = list_all_zones()
        cache.set(key, all_zones)
    can_edit = zone.can_edit(request)
    region = zone.zone_parent()
    # zonetype_label = zone.type_label()
    zonetype_label = zone.name
    if zone.zonetype_id == 3:
        zonetype_label = '%s-%s' % (zone.code, zone.name)
    elif zone.zonetype_id == 6:
        zonetype_label = '%s %s' % (zone.type_label(), zone.name)
    elif zone.zonetype_id == 7 and zone.code.startswith('M.'):
        zonetype_label = '%s %s' % (zone.name, _('of Roma'))
    return render(request, 'pois/zone_tag_index.html', {'zone': zone, 'region': region, 'zonetype_label': zonetype_label, 'zonetype_list': all_zones, 'tag_poitype_list': tag_poitype_list, 'can_edit': can_edit,})


def zone_tag_index_by_slug(request, zone_slug):
    zone = get_object_or_404(Zone, slug=zone_slug)
    return zone_tag_index(request, zone.id, zone=zone)

"""
180411 MMR non utilizzata
@xframe_options_exempt
def poitype_index(request):
    list_all = request.GET.get('all', None) is not None
    poitype_list = Poitype.objects.all().order_by('klass')
    poitype_instances_list = []
    for poitype in poitype_list:
        pois = Poi.objects.filter(poitype=poitype.klass, state=1)
        n = len(pois)
        if n or list_all:
            poitype_instances_list.append([poitype, n, pois[:1]])
    return render(request, 'pois/poitype_index.html', {'poitype_instances_list': poitype_instances_list,})
"""
@xframe_options_exempt
def category_index(request):
    list_all = request.GET.get('all', None) is not None
    if list_all:
        refresh_configuration()
    # poi_categories = settings.POI_CATEGORIES
    category_list = []
    poitype_instances_list = []
    last_category = None
    m = 0
    poitypes = Poitype.objects.all().order_by('klass')
    poitypes = Poitype.objects.all().exclude(klass__endswith = '0000').order_by('klass')
    for poitype in poitypes:
        klass = poitype.klass
        """
        if klass[4:] == '0000':
            continue
        """
        if not poitype.active:
            continue
        pois = Poi.objects.filter(poitype=klass, state=1)
        n = len(pois)
        if n or list_all:
            category = poitype.klass[:4]
            if category != last_category:
                if last_category:
                    last_code = list_all and last_category or ''
                    last_category_poitype = Poitype.objects.get(klass=last_category+'0000')
                    category_name = last_category_poitype.name
                    category_list.append([last_code, last_category_poitype, category_name, m, poitype_instances_list])
                poitype_instances_list = []
                last_category = category
                m = 0
            m += n
            prefix = list_all and poitype.klass or ''
            poitype_name = poitype.name
            theme_names = [theme.name for theme in poitype.get_themes()]
            poitype_instances_list.append([prefix, poitype, poitype_name, n, theme_names, pois[:1]])
    
    if m:
        last_code = list_all and last_category or ''
        last_category_poitype = Poitype.objects.get(klass=last_category+'0000')
        category_name = last_category_poitype.name
        category_list.append([last_code, last_category_poitype, category_name, m, poitype_instances_list])
    return render(request, 'pois/poitype_index.html', {'category_list': category_list,})

@xframe_options_exempt
def tag_detail(request, tag_id, tag=None):
    if not tag:
        tag = get_object_or_404(Tag, pk=tag_id)
    language = translation.get_language() or 'en'
    themes_cache = caches['themes']
    key = 'theme_%02d' % tag_id
    if not language.startswith(LANGUAGE_CODE) or request.GET.get('nocache', None):
        data_dict = None
    else:
        data_dict = themes_cache.get(key, None)
    if data_dict:
        print ('%s valid' % key)
    else:
        print ('%s invalid' % key)
        poitype_klasses = Poitype.objects.filter(tags=tag).values_list('klass', flat=True)
        tag_poitype_klasses = Poi.objects.filter(tags=tag, state=1).values_list('poitype_id', flat=True).distinct()
        klasses = list(set(poitype_klasses) | set(tag_poitype_klasses))
        poitypes = Poitype.objects.filter(klass__in=klasses).order_by('name')
        n_pois = 0
        poitype_instances_list = []
        for poitype in poitypes:
            pois = resources_by_tags_and_type([tag.id], poitype.klass)
            n = len(pois)
            if n:
                poitype_tag_ids = poitype.tags.all().values_list('id', flat=True)
                category_in_theme = tag.id in poitype_tag_ids
                # poitype_instances_list.append([poitype, n, category_in_theme, pois[:1]])
                poitype_instances_list.append([poitype.make_dict(), n, category_in_theme, pois[0].friendly_url()])
                n_pois += n
        n_poitype_list = len(poitype_instances_list)
        resto_2 = n_poitype_list % 2
        cols_2 = n_poitype_list // 2
        resto_3 = n_poitype_list % 3
        cols_3 = n_poitype_list // 3
        if resto_2 > 0:
            n_col_1 = cols_2+resto_2
        else: 
            n_col_1 = n_col_2 = cols_2
        list_2_1 = poitype_instances_list[:n_col_1]
        list_2_2 = poitype_instances_list[n_col_1:]
        if resto_3 > 0:
            n_col_1 = n_col_2_1 = cols_3+1
            n_col_2_2 = n_col_3 = cols_3*2+resto_3
        else: 
            n_col_1 = n_col_2_1 = cols_3
            n_col_2_2 = n_col_3 = cols_3*2
        list_3_1 = poitype_instances_list[:n_col_1]
        list_3_2 = poitype_instances_list[n_col_2_1:n_col_2_2]
        list_3_3 = poitype_instances_list[n_col_3:]
        data_dict = {'tag': tag.make_dict(), 'poitype_list': poitype_instances_list, 'list_2_1': list_2_1, 'list_3_1': list_3_1,'list_2_2': list_2_2, 'list_3_2': list_3_2,'list_3_3': list_3_3, }
        if language.startswith(LANGUAGE_CODE):
            try:
                themes_cache.set(key, data_dict)
            except:
                """
                MMR 20181701
                print (data_dict)
                """
                pass
    # return render_to_response('pois/tag_detail.html', {'tag': tag, 'poitype_list': poitype_instances_list,}, context_instance=RequestContext(request))
    return render(request, 'pois/tag_detail.html', data_dict)

def tag_detail_by_slug(request, tag_slug):
    tag = get_object_or_404(Tag, slug=tag_slug)
    return tag_detail(request, tag.id, tag=tag)

@xframe_options_exempt
def tag_zone_detail(request, tag_id, zone_id, tag=None, zone=None):
    if not tag:
        tag = get_object_or_404(Tag, pk=tag_id)
    if not zone:
        zone = get_object_or_404(Zone, pk=zone_id)
    poitype_klasses = Poitype.objects.filter(tags=tag).values_list('klass', flat=True)
    q = make_zone_subquery(zone)
    tag_poitype_klasses = Poi.objects.filter(q & Q(tags=tag, state=1)).values_list('poitype_id', flat=True).distinct()
    klasses = list(set(poitype_klasses) | set(tag_poitype_klasses))
    klasses.sort()
    poitypes = Poitype.objects.filter(klass__in=klasses)
    n_pois = 0
    poitype_instances_list = []
    for poitype in poitypes:
        pois = resources_by_tags_and_type([tag.id], poitype.klass, q=q)
        n = len(pois)
        if n:
            poitype_tag_ids = poitype.tags.all().values_list('id', flat=True)
            category_in_theme = tag.id in poitype_tag_ids
            poitype_instances_list.append([poitype, n, category_in_theme])
            n_pois += n
    return render(request,'pois/tag_zone_detail.html', {'tag': tag, 'zone': zone, 'poitype_list': poitype_instances_list,} )

def tag_zone_detail_by_slug(request, tag_slug, zone_slug):
    tag = get_object_or_404(Tag, slug=tag_slug)
    zone = get_object_or_404(Zone, slug=zone_slug)
    return tag_zone_detail(request, tag.id, zone.id, tag=tag, zone=zone)

@xframe_options_exempt
def poitype_detail(request, klass, poitype=None):
    list_all = request.GET.get('all', '')
    zone_list = [];  poi_dict_list = []
    max_count = 0; min_count = 10000
    if not poitype:
        poitype = get_object_or_404(Poitype, klass=klass)
    zone = get_object_or_404(Zone, code='ROMA')
    theme = request.GET.get('theme', '')
    if theme and not theme in poitype.tags.all():
        theme_id = int(theme)
        theme_list = [get_object_or_404(Tag, pk=theme_id)]
    else:
        theme_id = None
        theme_list = poitype.tags.all()
    region = 'ROMA'
    language = translation.get_language() or 'en'
    categories_cache = caches['categories']
    key = 'cat_%s' % klass
    if not language.startswith('it') or request.GET.get('nocache', None) or theme:
        data_dict = None
    else:
        data_dict = categories_cache.get(key, None)
        if data_dict:
            print ('%s valid' % key)
        else:
            print ('%s invalid' % key)
    if not data_dict:
        help_text = FlatPage.objects.get(url='/help/category/').content
        # if theme and not theme in poitype.tags.all():
        if theme_id:
            poi_list = resources_by_tags_and_type([theme_id], poitype.klass)
        else:
            if poitype.active:
                poi_list = Poi.objects.select_related().filter(poitype=poitype.klass, state=1).order_by('name')
            else:
                klasses = poitype.sub_types(return_klasses=True)
                poi_list = Poi.objects.filter(poitype_id__in=klasses, state=1).order_by('name')
            if poi_list.count() > MAX_POIS and not list_all:
                zones = Zone.objects.filter(zonetype_id=0).exclude(code='ROMA')
                zone_list = zone_list_no_sorted = []
                for zone in zones:
                    pois = resources_by_category_and_zone(klass, zone)
                    if pois:
                        n = pois.count()
                        max_count = max(n, max_count)
                        min_count = min(n, min_count)
                        zone_dict = zone.make_dict()
                        zone_dict['url'] = '/categoria/%s/zona/%s/' % (poitype.slug, zone.slug)
                        zone_dict['count'] = n
                        zone_list_no_sorted.append(zone_dict)
                        zone_list = sorted(zone_list_no_sorted, key=lambda k: k['name'].lower())
                if zone_list:
                    for item in zone_list:
                        if 'provincia' in item['name'].lower():
                            region = 'LAZIO'
                            break
                zone = None
                help_text = FlatPage.objects.get(url='/help/big-list/').content
        if not zone_list:
            poi_dict_list_no_sorted = [poi.make_dict(list_item=True) for poi in poi_list]
            poi_dict_list = sorted(poi_dict_list_no_sorted, key=lambda k: k['name'].lower())
            for item in poi_dict_list:
                if item['comune'][1] != 'roma':
                    region = 'LAZIO'
                    break
        """
        set_focus(request, tags=[theme.id for theme in theme_list])
        focus_set_category(request, klass)
        """
        sub_types = not poitype.active and [{ 'name': p.name, 'slug': p.slug } for p in poitype.sub_types()] or []
        poitype_name = poitype.name
        if poitype.short:
            poitype_short = poitype.short
        else:
            ancestor_klass = '%s0000' % (poitype.klass[:4])
            ancestor=Poitype.objects.get(klass=ancestor_klass)
            if ancestor.short:
                poitype_short = ancestor.short
            else:
                poitype_short = _("easily find addresses, contacts and information on services.")
        poitype = { 'name': poitype.name,  'slug': poitype.slug, 'active': poitype.active }
        if sub_types:
            poitype['sub_types'] = sub_types
        data_dict = {'help': help_text, 'poitype': poitype, 'theme_list': theme_list, 'poi_dict_list': poi_dict_list, 'region': region, 'zone_list': zone_list, 'min': min_count, 'max': max_count}
        data_dict['zone'] = zone
        if region == 'ROMA':
            data_dict['title_page'] = '%s %s' % (poitype_name, _('in Roma'))
            data_dict['short_page'] = '%s %s: %s' % (poitype_name,_('in Roma'),poitype_short)
        else:
            data_dict['title_page'] = '%s %s' % (poitype_name, _('in Lazio'))
            data_dict['short_page'] = '%s %s: %s' % (poitype_name,_('in Lazio'),poitype_short)
        if language.startswith('it') and not theme:
            try:
                categories_cache.set(key, data_dict)
            except:
                """
                MMR 20181701
                print (data_dict)
                """
                pass
    return render(request, 'pois/poitype_detail.html', data_dict)

def poitype_detail_by_slug(request, klass_slug):
    poitype = get_object_or_404(Poitype, slug=klass_slug)
    return poitype_detail(request, poitype.klass, poitype)

@xframe_options_exempt
def poitype_tag_detail(request, klass, tag_id, poitype=None, tag=None):
    if not poitype:
        poitype = get_object_or_404(Poitype, klass=klass)
    if not tag:
        tag = get_object_or_404(Tag, pk=tag_id)
    zone = get_object_or_404(Zone, code='ROMA') 
    poi_list = resources_by_tags_and_type([tag_id], klass)
    theme_list = poitype.tags.all()
    help_text = FlatPage.objects.get(url='/help/category/').content
    poi_dict_list_no_sorted = [poi.make_dict(list_item=True) for poi in poi_list]
    poi_dict_list = sorted(poi_dict_list_no_sorted, key=lambda k: k['name'].lower())
    region = 'ROMA'
    for item in poi_dict_list:
       if item['comune'][1] != 'roma':
           region = 'LAZIO' 
           break
    data = {'help': help_text, 'poitype': poitype, 'region': region, 'zone': zone, 'theme_list': theme_list, 'poi_dict_list': poi_dict_list,}
    if not tag in poitype.tags.all():
        data['theme'] = tag
    if poitype.short:
        poitype_short = poitype.short
    else:
        ancestor_klass = '%s0000' % (poitype.klass[:4])
        ancestor=Poitype.objects.get(klass=ancestor_klass)
        if ancestor.short:
            poitype_short = ancestor.short
        else:
            poitype_short = _("easily find addresses, contacts and information on services.")
    if region == 'ROMA':
        data['title_page'] = '%s %s' % (poitype.name, _('in Roma'))
        data['short_page'] = '%s %s: %s' % (poitype.name,_('in Roma'),poitype_short)
    else:
        data['title_page'] = '%s %s' % (poitype.name, _('in Lazio'))
        data['short_page'] = '%s %s: %s' % (poitype.name,_('in Lazio'),poitype_short)
    return render(request, 'pois/poitype_tag_detail.html', data)

def poitype_tag_detail_by_slugs(request, klass_slug, tag_slug):
    poitype = get_object_or_404(Poitype, slug=klass_slug)
    tag = get_object_or_404(Tag, slug=tag_slug)
    return poitype_tag_detail(request, poitype.klass, tag.id, poitype=poitype, tag=tag)

@xframe_options_exempt
def poitype_zone_detail(request, klass, zone_id, poitype=None, zone=None):
    if not poitype:
        poitype = get_object_or_404(Poitype, klass=klass)
    if not zone:
        zone = get_object_or_404(Zone, pk=zone_id)
    language = translation.get_language() or 'en'
    catzones_cache = caches['catzones']
    key = 'cat_%s_zone%04d' % (klass, zone_id)
    region = 'ROMA'
    if not language.startswith('it') or request.GET.get('nocache', None):
        data_dict = None
    else:
        data_dict = catzones_cache.get(key, None)
    if data_dict:
        print ('%s valid' % key)
    else:
        print ('%s invalid' % key)
        poi_list = resources_by_category_and_zone(klass, zone, select_related=True)
        zone_list = zone_list_no_sorted = []
        if zone.zonetype_id == 0:
            zones = Zone.objects.filter(zonetype_id=0).exclude(code='ROMA')
            for z in zones:
                if z.id != zone.id:
                    pois = resources_by_category_and_zone(klass, z)
                    if pois:
                        n = pois.count()
                        """
                        z.count = n
                        z.url = '/categoria/%s/zona/%s/' % (poitype.slug, z.slug)
                        """
                        url = '/categoria/%s/zona/%s/' % (poitype.slug, z.slug)
                        z = z.make_dict()
                        z['count'] = n
                        z['url'] = url
                        zone_list_no_sorted.append(z)
                        zone_list = sorted(zone_list_no_sorted, key=lambda k: k['name'].lower())
        theme_list = [ t.make_dict() for t in poitype.tags.all()]
        sub_types = not poitype.active and [{ 'name': p.name, 'slug': p.slug } for p in poitype.sub_types()] or []
        poitype_name = poitype.name
        if poitype.short:
            poitype_short = poitype.short
        else:
            ancestor_klass = '%s0000' % (poitype.klass[:4])
            ancestor=Poitype.objects.get(klass=ancestor_klass)
            if ancestor.short:
                poitype_short = ancestor.short
            else:
                poitype_short = _("easily find addresses, contacts and information on services.")
        poitype = { 'name': poitype.name,  'slug': poitype.slug, 'active': poitype.active }
        if sub_types:
            poitype['sub_types'] = sub_types
        help_text = FlatPage.objects.get(url='/help/category/').content
        poi_dict_list_no_sorted = [poi.make_dict(list_item=True) for poi in poi_list]
        poi_dict_list = sorted(poi_dict_list_no_sorted, key=lambda k: k['name'].lower())
        if zone_list and poi_dict_list: 
            for item in zone_list:
                if 'provincia' in item['name'].lower():
                    region = 'LAZIO' 
                    break
        elif poi_dict_list:
            for item in poi_dict_list:
                if item['comune'][1] != 'roma':
                    region = 'LAZIO' 
                    break
        else:
            region = zone.zone_parent()
        data_dict = {'help': help_text, 'poitype': poitype, 'theme_list': theme_list, 'poi_dict_list': poi_dict_list, 'zone_list': zone_list, 'region': region}
        data_dict['zone'] = zone
        
        if zone.code.startswith('S.'):
            data_dict['title_page'] = '%s - %s (%s)' % (poitype_name, zone.name, _('quarter extension'))
            data_dict['short_page'] = '%s - %s (%s): %s' % (poitype_name, zone.name, _('quarter extension'), poitype_short)
        else:
            data_dict['title_page'] = '%s - %s' % (poitype_name, zone.name,)
            data_dict['short_page'] = '%s - %s: %s' % (poitype_name, zone.name, poitype_short)

        if language.startswith('it'):
            try:
                catzones_cache.set(key, data_dict)
            except:
                """
                MMR 20181701
                print (data_dict)
                """
                pass
    return render(request, 'pois/poitype_zone_detail.html', data_dict)

def poitype_zone_detail_by_slugs(request, klass_slug, zone_slug):
    poitype = get_object_or_404(Poitype, slug=klass_slug)
    zone = get_object_or_404(Zone, slug=zone_slug)
    return poitype_zone_detail(request, poitype.klass, zone.id, poitype=poitype, zone=zone)

@login_required
def poi_index(request):
    poi_list = Poi.objects.all()
    return render(request, 'pois/poi_index.html', {'poi_list': poi_list,})

@xframe_options_exempt
def poi_detail(request, poi_id, poi=None):
    if not poi:
        poi = get_object_or_404(Poi, pk=poi_id)
        return HttpResponseRedirect('/risorsa/%s/' % poi.slug)
    language = translation.get_language() or 'en'
    can_edit = poi.can_edit(request)
    focus_set_category(request, poi.poitype_id)
    """
    focus_add_themes(request, poi.get_themes_indirect(return_ids=True))
    focus_add_themes(request, poi.get_themes(return_ids=True))
    """
    user_agent = get_user_agent(request)
    pois_cache = caches['pois']
    key = 'poi%05d' % poi_id
    if not language.startswith('it') or request.GET.get('nocache',None):
        data_dict = None
    else:
        data_dict = pois_cache.get(key, None)
    if not data_dict:
        print ('invalid cache for ', key)
        poi_dict = poi.make_dict() # 140603
        poi_dict['typecard'] = poi.getTypecard
        zones = Zone.objects.filter(pois=poi_id, zonetype__id__in=[3,7]).order_by('zonetype__id')
        zone_list = []
        macrozone = None
        zone_parent = None
        for zone in zones:
            if zone.zonetype_id == 3: # zona toponomastica
                zone_list.append({ 'name': '%s (%s)' % (zone.name, zone.code), 'url': '/zona/%s/' % zone.slug, 'slug': zone.slug})
            else: # municipio
                if zone.code.startswith('M'):
                    zone_list.append({ 'name': zone.name, 'url': '/zona/%s/' % zone.slug, 'slug': zone.slug})
                zone_parent = zone.zone_parent()
                macrozone = zone.get_macrozone_slug()
        poi_dict['zone_parent'] = zone_parent
        hosted_list = Poi.objects.filter(host=poi).order_by('name')
        hosted_list = [{ 'name': p.name, 'url': p.friendly_url()} for p in hosted_list if p.state == 1]
        poi_chain_list = poi.get_chain_pois()
        if poi_chain_list:
            poi_chain_list=[p for p in poi_chain_list if p != poi and Poi.objects.filter(pk = p.id, state = 1)]
            print(poi_chain_list)
        poi_list = Poi.objects.filter(pois=poi, state=1).order_by('name')
        poi_list = [{ 'name': p.name, 'url': p.friendly_url()} for p in poi_list if not p in poi_chain_list]
        n_caredby = Poi.objects.filter(careof=poi).count()
        poitype = poi.poitype
        if poitype:
            if macrozone:
                poitype = { 'name': poitype.name, 'url': '/categoria/%s/zona/%s/' % (poitype.slug, macrozone)}
            else:
                poitype = { 'name': poitype.name, 'url': poitype.friendly_url()}
        
        theme_list = [{ 'id': theme.id, 'name': theme.name, 'slug': theme.slug } for theme in poi.get_all_themes() if theme.id != 49]
        data_dict = {'poi_dict': poi_dict, 'poitype': poitype, 'theme_list': theme_list, 'hosted_list': hosted_list, 'zone_list': zone_list, 'poi_list': poi_list, 'poi_chain_list': poi_chain_list, 'n_caredby': n_caredby,}
        if macrozone:
            data_dict['macrozone'] = macrozone
        if language.startswith('it'):
            pois_cache.set(key, data_dict)
    feeds = []
    for f in poi.get_feeds():
        entries = []
        for e in f.entries:
            try: entry = { 'title': e.title, 'link': e.link }
            except: continue
            try: entry['summary'] = e.summary
            except: pass
            try: entry['content'] = e.content[0].value
            except: pass
            try: entry['date'] = e.date
            except:
                try: entry['date'] = e.published
                except: pass
            entries.append(entry)
        feeds.append({ 'title': f.feed.title, 'entries': entries })
    data_dict['can_edit'] = can_edit
    data_dict['feeds'] = feeds
    data_dict['user_agent'] = user_agent
    return render(request, 'pois/poi_detail.html', data_dict)

def poi_detail_by_slug(request, poi_slug):
    poi = get_object_or_404(Poi, slug=poi_slug)
    if poi.state == 1 or poi.can_edit(request):
        poi_id = poi.id
    else:
        poi = None
        poi_id = -1
    return poi_detail(request, poi_id, poi)

def street_autocomplete(request):
    MIN_CHARS = 3
    q = request.GET.get('q', None)
    results = []
    if q and len(q) >= MIN_CHARS:
        qs = Odonym.objects.filter(name__icontains=q).order_by('name')
        results = [{'id': street.id, 'text': street.name} for street in qs]
    body = json.dumps({'results': results, 'pagination': {'more': False}})
    return HttpResponse(body, content_type='application/json')

def poi_promote(request):
    flatpage = FlatPage.objects.get(url='/risorse/promuovi/')
    text_body = flatpage.content
    flatpage = FlatPage.objects.get(url='/risorse/promuovi-desktop/')
    table_desktop = flatpage.content
    flatpage = FlatPage.objects.get(url='/risorse/promuovi-tablet/')
    table_tablet = flatpage.content
    flatpage = FlatPage.objects.get(url='/risorse/promuovi-phone/')
    table_phone = flatpage.content
    return render(request, 'pois/poi_promote.html', {'text_body': text_body, 'table_desktop': table_desktop, 'table_tablet': table_tablet, 'table_phone': table_phone, })

def poi_edit(request, poi_id):
    poi = get_object_or_404(Poi, pk=poi_id)
    form = PoiUserForm(instance=poi)
    return (request, 'pois/poi_edit.html', {'poi': poi, 'form': form})

from django.core.mail import send_mail
from roma.settings import SERVER_EMAIL, SITE_NAME
def poi_new(request):
    flatpage = FlatPage.objects.get(url='/risorse/segnala/')
    text_body = flatpage.content
    user = request.user
    if user.is_authenticated:
        fullname ='%s %s' % (user.first_name, user.last_name)
        form = PoiUserForm(initial={'fullname': fullname,'user_email': user.email})
    else:
        form = PoiUserForm()
    return render(request, 'pois/poi_edit.html', {'poi': '', 'form': form, 'text_body': text_body})

def poi_save(request):
    flatpage = FlatPage.objects.get(url='/risorse/segnala/')
    text_body = flatpage.content
    if request.POST:
        form = PoiUserForm(request.POST)
        if form.is_valid():
            # human = True
            recaptcha = request.POST.get('g-recaptcha-response')
            data = {
                'secret': settings.GOOGLE_RECAPTCHA_SKEY,
                'response': recaptcha
            }
            r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
            result_captcha = r.json()
            if result_captcha['success']:
                web = request.POST['web']
                facebook = request.POST['facebook']
                now = datetime.datetime.now()
                fullname = request.POST['fullname']
                user_email = request.POST['user_email']
                notes = """----- risorsa segnalata in data %s -----
----- da %s - %s -----
""" % (now, fullname, user_email)
                poi = form.save()
                if request.user.is_authenticated:
                    poi.owner = request.user
                poi.notes = notes
                if web and facebook:
                    poi.web = '%s\n%s' % (web, facebook)
                elif facebook:
                    poi.web = facebook
                poi.save()
                subject='%s - nuova risorsa: %s' % (SITE_NAME, poi.name)
                message='risorsa: %s (id: %s)\n\n----- risorsa segnalata in data %s -----\n\n-----da: %s - %s -----' % (poi.name, poi.id, now, fullname, user_email)
                result = send_mail(
                    subject,
                    message,
                    SERVER_EMAIL,
                    [SERVER_EMAIL,],
                    fail_silently=False,
                )
                subject='%s - risorsa segnalata: %s' % (SITE_NAME, poi.name)
                message="Gentile %s,\n\n Grazie per averci segnalato la risorsa --- %s ---\nAppena potremo pubblicheremo il profilo della risorsa, dopo avere rivisto ed eventualmente integrato l'informazione da lei fornita.\n\nLo staff di Romapaese\n\n http:%s" % (fullname, poi.name, request.META['HTTP_HOST'])
                result = send_mail(
                    subject,
                    message,
                    SERVER_EMAIL,
                    [user_email],
                    fail_silently=False,
                )
                return HttpResponseRedirect('/nuova-risorsa/%s/' % poi.id)
            else:
                nocaptcha = _('Invalid reCAPTCHA. Please try again.')
                return render(request, 'pois/poi_edit.html', {'form': form, 'text_body': text_body, 'nocaptcha': nocaptcha})
        else:
            return render(request, 'pois/poi_edit.html', {'form': form, 'text_body': text_body, 'nocaptcha': ''})
    else:
        return poi_new(request)

def poi_view(request,poi_id):
    poi = get_object_or_404(Poi, pk=poi_id)
    flatpage = FlatPage.objects.get(url='/risorse/riscontro/')
    text_body = flatpage.content
    poi.comune = poi.get_comune()
    return render(request, 'pois/poi_view.html', {'poi': poi, 'text_body': text_body})

def poi_add_note(request, poi_id, poi=None):
    flatpage = FlatPage.objects.get(url='/risorsa/annota/')
    text_body = flatpage.content
    if not poi:
        poi = get_object_or_404(Poi, pk=poi_id)
    form = PoiAnnotationForm(initial={'id': poi_id})
    return render(request, 'pois/poi_feedback.html', {'poi': poi, 'form': form, 'text_body': text_body})

def poi_add_note_by_slug(request, poi_slug):
    poi = get_object_or_404(Poi, slug=poi_slug)
    return poi_add_note(request, poi.id, poi=poi)

def poi_save_note(request):
    poi_id = int(request.POST.get('id', 0))
    poi = get_object_or_404(Poi, pk=poi_id)
    flatpage = FlatPage.objects.get(url='/risorsa/annota/')
    text_body = flatpage.content
    form = PoiAnnotationForm(request.POST)
    if form.is_valid():
        recaptcha = request.POST.get('g-recaptcha-response')
        data = {
            'secret': settings.GOOGLE_RECAPTCHA_SKEY,
            'response': recaptcha
        }
        r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
        result_captcha = r.json()
        if result_captcha['success']:
            now = datetime.datetime.now()
            comment = request.POST['notes']
            fullname = request.POST['name']
            email = request.POST['email']
            poi.notes = """----- commento in data %s -----
%s
%s - %s
-----
%s
""" % (now, comment, fullname, email, poi.notes)
            poi.save()
            subject='%s - nota su risorsa: %s' % (SITE_NAME, poi.name)
            message='risorsa: %s (id: %s) http://%s/risorsa/%s/\n\n----- nota in data %s -----\n\n nota inviata tramite il sito da: %s - %s' % (poi.name, poi.id, request.META['HTTP_HOST'], poi.slug, now, fullname, email)
            result = send_mail(
                subject,
                message,
                SERVER_EMAIL,
                [SERVER_EMAIL],
                fail_silently=False,
            )
            return HttpResponseRedirect('/risorsa/%s/?comment=true' % poi.slug)
        else:
            nocaptcha = _('Invalid reCAPTCHA. Please try again.')
            return render(request, 'pois/poi_feedback.html', {'poi_name': poi.name,'form': form, 'text_body': text_body,'nocaptcha': nocaptcha})
    else:
        return render(request, 'pois/poi_feedback.html', {'poi_name': poi.name, 'form': form, 'text_body': text_body, 'nocaptcha': ''})

def pois_recent(request, n=MAX_POIS):
    user = request.user
    if user.is_superuser or user.is_staff:
        instances = Poi.objects.select_related().filter(state=1).order_by('-id')[:n]
        poi_dict_list = [poi.make_dict() for poi in instances]
        return render(request, 'pois/pois_report/poi_list.html', {'list_type': 'recent', 'poi_dict_list': poi_dict_list, 'count': instances.count()})
    return HttpResponseRedirect('/')
    
def pois_updates(request, n=MAX_POIS):
    user = request.user
    if user.is_superuser or user.is_staff:
        last_id = Poi.objects.latest('id').id
        instances = Poi.objects.select_related().filter(id__lt=last_id-MAX_POIS, state=1).order_by('-modified')[:n]
        poi_dict_list = [poi.make_dict() for poi in instances]
        return render(request, 'pois/pois_report/poi_list.html', {'list_type': 'updates', 'poi_dict_list': poi_dict_list, 'count': instances.count()})
    return HttpResponseRedirect('/')

def my_resources(request, n=MAX_POIS):
    n = request.GET.get('n', n)
    n = int(n)
    poi_dict_list = []
    count = 0
    if request.user.is_superuser or request.user.is_staff:
        instances = Poi.objects.filter(owner=request.user).order_by('-id')[:n]
        count = instances.count()
        poi_dict_list = [poi.make_dict() for poi in instances]
        return render(request, 'pois/pois_report/poi_list.html', {'list_type': 'my_resources', 'poi_dict_list': poi_dict_list, 'count': count})
    return HttpResponseRedirect('/')
    
def poi_contributors(request):
    user = request.user
    if user.is_superuser or user.is_staff:
        users = User.objects.annotate(num_pois=Count('poi_owner')).filter(num_pois__gt=0).order_by('-num_pois')
        return render(request, 'pois/pois_report/poi_contributors.html', { 'user_list': users, })
    return HttpResponseRedirect('/')

def poi_zonize(request, poi_id):
    if request.user.is_superuser or request.user.is_staff:
        poi = get_object_or_404(Poi, pk=poi_id)
        poi.update_zones(zonetypes=[1, 3, 7])
        return HttpResponseRedirect('/admin/pois/poi/%s/' % poi_id)
    return HttpResponseRedirect('/')
    
def pois_update_colocations(request):
    if request.user.is_superuser or request.user.is_staff:
        pois = Poi.objects.exclude(host__isnull=True)
        n = 0
        for poi in pois:
            host = poi.host
            if poi.point == host.point:
                pass
            else:
                poi.point = host.point
                poi.save()
                n += 1
        html = u"""
<html><body>
<div>Aggiornato la posizione di %d risorse con quella della risorsa ospitante.
</body></html>
""" % n
        return HttpResponse(html, content_type='text/html')
    return HttpResponseRedirect('/')
        

def poi_analysis(request):
    no_geo_list = []
    no_theme_list = []
    todo_list = []
    comment_list = []
    notes_list = []
    web_list = web_list_no_sorted = []
    feeds_list = feed_list_no_sorted = []
    poi_list = []
    state = -1
    if request.user.is_superuser or request.user.is_staff:
        value_get = request.GET.get('field','')
        state = request.GET.get('state','')
        if state:
            qs = Poi.objects.filter(state=state)
        else:
            qs = Poi.objects.all()
        if value_get in ['web']:
            web_list_no_sorted = [poi.make_short_dict() for poi in qs.exclude(web__isnull=True).exclude(web__exact='')]
            web_list = sorted(web_list_no_sorted, key=lambda k: k['name'].lower())
        if value_get in ['feeds']:
            feeds_list_no_sorted = [poi.make_short_dict() for poi in qs.exclude(feeds__isnull=True).exclude(feeds__exact='')]
            feeds_list = sorted(feeds_list_no_sorted, key=lambda k: k['name'].lower())
        if value_get in ['all', 'geo']:
            no_geo_list = [poi.make_dict() for poi in qs.filter(point__isnull=True).order_by('-modified')]
        if value_get in ['all', 'theme']:
            no_theme_list = [poi.make_dict() for poi in qs.filter(tags__isnull=True, poitype__tags__isnull=True).order_by('-modified')]
        if value_get in ['all','todo','comment','notes']:
            poi_list = qs.exclude(notes='').exclude(notes__isnull=True).order_by('-modified')
        if poi_list:
            if value_get in ['all','todo']:
                for poi in poi_list:
                    notes = poi.notes
                    if notes[0] != '\r' and notes[0] != '\n':
                        todo = notes.split('\n')[0]
                        item = poi.make_dict()
                        item.update({'notes': todo})
                        todo_list.append(item)
            if value_get in ['all','comment']:
                for poi in poi_list:
                    notes = poi.notes
                    if notes.count('----- commento'):
                        item = poi.make_dict()
                        item.update({'notes': notes})
                        comment_list.append(item)
            if value_get in ['all','notes']:
                for poi in poi_list:
                    notes = poi.notes
                    if notes:
                        item = poi.make_dict()
                        item.update({'notes': notes})
                        notes_list.append(item)
        return render(request, 'pois/pois_report/poi_analysis.html', {'stato': state, 'web_list': web_list, 'feeds_list': feeds_list, 'no_geo_list': no_geo_list, 'no_theme_list': no_theme_list, 'todo_list': todo_list, 'comment_list': comment_list, 'notes_list': notes_list,})
    return HttpResponseRedirect('/')


def decimal_to_exagesimal(coord):
    degrees = int(coord)
    coord = coord - degrees
    minutes = int(coord*60)
    coord = coord*60 - minutes
    seconds = int(coord*60)
    coord = coord*60 - seconds
    rest = int(coord * 100)
    return u"%d° %d' %d.%d''" % (degrees, minutes, seconds, rest)

def safe_string(s):
    s = '"%s"' % s.replace('"', '""')
    return s

def pois_to_excel(poi_list):
    col_headers = ['municipio', 'nome', 'toponimo', 'civico', 'cap', 'città', 'email', 'web', 'telefono', 'lon', 'lat', 'pos.x', 'pos.y']
    header = ';'.join(col_headers)
    lines = [header]
    for poi in poi_list:
        poi_dict = poi.make_dict()
        municipio = ''
        for zone in poi.zones.all():
            if zone.zonetype_id == MUNICIPIO:
                municipio = zone.code[2:]
        point = poi.point
        email = ', '.join(poi.clean_list(poi.email))
        web = ', '.join([items[0] for items in poi.clean_webs()])
        phone = ', '.join(poi.clean_phones())
        x = y = lon = lat = ''
        if point:
            x = point.x
            y = point.y
            lon = '%sE' % decimal_to_exagesimal(x)
            lat = '%sN' % decimal_to_exagesimal(y)
        # line_values = [municipio, safe_string(poi_dict['name']), safe_string(poi_dict['street_name']), poi_dict['number'], poi_dict['cap'], 'Roma', email, web, phone, lon, lat, str(x), str(y)]
        line_values = [municipio, safe_string(poi_dict['name']), safe_string(poi_dict['street_name']), poi_dict['number'], poi_dict['cap'], poi_dict['comune'], email, web, phone, lon, lat, str(x), str(y)]
        lines.append(';'.join(line_values))
    return '\n'.join(lines)

def poi_network(request, poi_id, poi=None):
    list_all = request.GET.get('all', None)
    formato = request.GET.get('format', None)
    zone_list = zone_list_no_sorted = []
    poi_dict_list = []
    max_count = 0
    min_count = 10000
    if not poi:
        poi = get_object_or_404(Poi, pk=poi_id)
    poi_list = Poi.objects.filter(pois=poi, state=1).order_by('name')
    zone = get_object_or_404(Zone, code='ROMA')
    help_text = FlatPage.objects.get(url='/help/network/').content
    parent = poi
    if formato:
        excel_data = pois_to_excel(poi_list)
        filename = slugify(poi.name)
        response = HttpResponse(excel_data, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename="%s.csv"' % filename
        return response
    if poi_list.count() > MAX_POIS and not list_all:
        zones = Zone.objects.filter(zonetype_id=0).exclude(code='ROMA')
        for zone in zones:
            q = make_zone_subquery(zone)
            pois = Poi.objects.filter(q & Q(pois=poi, state=1))
            if pois:
                n = pois.count()
                max_count = max(n, max_count)
                min_count = min(n, min_count)
                zone_dict = zone.make_dict()
                zone_dict['count'] = n
                zone_dict['url'] = '/rete/%s/zona/%s/' % (poi.slug, zone.slug)
                # zone_list.append(zone_dict)
                zone_list_no_sorted.append(zone_dict)
                zone_list = sorted(zone_list_no_sorted, key=lambda k: k['name'].lower())
        zone = None
        help_text = FlatPage.objects.get(url='/help/big-list/').content
    else:
        poi_dict_list = [poi.make_dict(list_item=True) for poi in poi_list]
    region = 'ROMA'
    if zone_list and poi_list:
        for item in zone_list:
            if 'provincia' in item['name'].lower():
                region = 'LAZIO' 
                break
    elif poi_dict_list:
        for item in poi_dict_list:
            if item['comune'][1] != 'roma':
                region = 'LAZIO' 
                break
    return render(request, 'pois/network_detail.html', {'relation': 'affiliated', 'help': help_text, 'zone': zone, 'parent': parent, 'poi_dict_list': poi_dict_list, 'zone_list': zone_list, 'min': min_count, 'max': max_count,'region': region,})

def poi_network_by_slug(request, poi_slug):
    poi = get_object_or_404(Poi, slug=poi_slug)
    return poi_network(request, poi.id, poi)

def poi_network_zone(request, poi_id, zone_id, poi=None, zone=None):
    if not poi:
        poi = get_object_or_404(Poi, pk=poi_id)
    if not zone:
        zone = get_object_or_404(Zone, pk=zone_id)
    q = make_zone_subquery(zone)
    poi_list = Poi.objects.filter(q & Q(pois=poi, state=1)).order_by('name')
    help_text = FlatPage.objects.get(url='/help/network/').content
    parent = poi
    poi_dict_list = [poi.make_dict(list_item=True) for poi in poi_list]
    zone_name = zone.name
    region = zone.zone_parent().lower()
    if zone_name.lower().startswith(region):
        region = zone_name
        zone_name = ''
    if poi_dict_list:
        for item in poi_dict_list:
            if item['comune'][1] != 'roma':
                region = 'lazio' 
                break
    return render(request, 'pois/network_detail.html', {'relation': 'affiliated', 'help': help_text, 'zone_name': zone_name, 'parent': parent, 'zone': zone, 'poi_dict_list': poi_dict_list, 'region': region})

def poi_network_zone_by_slug(request, poi_slug, zone_slug):
    poi = get_object_or_404(Poi, slug=poi_slug)
    zone = get_object_or_404(Zone, slug=zone_slug)
    return poi_network_zone(request, poi.id, zone.id, poi=poi, zone=zone)

def resource_map(request, poi_id, poi=None):
    if not poi:
        poi = get_object_or_404(Poi, pk=poi_id)
    poi_list = Poi.objects.filter(careof=poi, state=1).order_by('name')
    zone = get_object_or_404(Zone, code='ROMA')
    help_text = FlatPage.objects.get(url='/help/map/').content
    parent = poi
    # poi_dict_list = [poi.make_dict() for poi in poi_list]
    poi_dict_list = [poi.make_dict(list_item=True) for poi in poi_list]
    region = 'ROMA'
    if poi_dict_list:
        for item in poi_dict_list:
            if item['comune'][1] != 'roma':
                region = 'LAZIO' 
                break
    return render(request, 'pois/network_detail.html', {'relation': 'caredby', 'help': help_text, 'zone': zone, 'parent': parent, 'poi_dict_list': poi_dict_list, 'region': region})

def resource_map_by_slug(request, poi_slug):
    poi = get_object_or_404(Poi, slug=poi_slug)
    return resource_map(request, poi.id, poi)

from django.db.models import Count
def resource_networks(request):
    user = request.user
    if user.is_superuser or user.is_staff:
        pois = Poi.objects.filter(state=1).exclude(poi__pois=None)
        if POI_CLASSES:
            pois = pois.filter(poitype_id__in=POI_CLASSES)
        pois = pois.annotate(num_pois=Count('poipoi')).order_by('-num_pois')
        poi_dict_list = []
        for poi in pois:
            poi_dict = poi.make_dict(list_item=True)
            if poi.num_pois > 3:
                poi_dict['num_pois'] = poi.num_pois
                poi_dict_list.append(poi_dict)
        return render(request, 'pois/pois_report/poi_list.html', {'list_type': 'networks', 'poi_dict_list': poi_dict_list, 'count': len(poi_dict_list)})
    return HttpResponseRedirect('/')

def resource_maps(request):
    user = request.user
    if user.is_superuser or user.is_staff:
        instances = Poi.objects.filter(state=1).exclude(poi_careof=None).annotate(num_pois=Count('poi__careof')).order_by('-num_pois')
        poi_dict_list = []
        for instance in instances:
            pois_map = Poi.objects.filter(careof=instance)
            num_pois = len(pois_map)
            if num_pois > 3 and num_pois < 100:
                # poi_dict = instance.make_dict()
                poi_dict = instance.make_dict(list_item=True)
                poi_dict['num_pois'] = num_pois
                poi_dict_list.append(poi_dict)
        return render(request, 'pois/pois_report/poi_list.html', {'list_type': 'maps', 'poi_dict_list': poi_dict_list, 'count': len(poi_dict_list)})
    return HttpResponseRedirect('/')

def viewport_get_pois(request, viewport, street_id=None, tags=[]):
    w, s, e, n = viewport
    geom = Polygon(LinearRing([Point(w, n), Point(e, n), Point(e, s), Point(w, s), Point(w, n)]),srid=srid_OSM)
    geom.transform(srid_GPS)
    geo_query = Q(point__within=geom)
    state_query = Q(state=1)
    if street_id:
        street = get_object_or_404(Odonym, pk=street_id)
        street_query = Q(street=street)
        pois = Poi.objects.filter((street_query | geo_query) & state_query).order_by('name')
    elif tags:
        pois = resources_by_tags(tags, q=geo_query)
    else:
        pois = Poi.objects.filter(geo_query & state_query).order_by('name')
    return pois

def set_viewport(request):
    w = float(request.GET['left'])
    s = float(request.GET['bottom'])
    e = float(request.GET['right'])
    n = float(request.GET['top'])
    viewport = [w, s, e, n]
    set_focus(request, key='viewport', value=viewport)
    json_data = json.dumps({'HTTPRESPONSE': 1, 'data': ''})
    return HttpResponse(json_data, content_type="application/x-json")


# riporta le risorse interne alla viewport specificata dalla querystring
def viewport_pois(request):
    w = float(request.GET['left'])
    s = float(request.GET['bottom'])
    e = float(request.GET['right'])
    n = float(request.GET['top'])
    street_id = int(request.GET.get('street', 0))
    max_pois = int(request.GET.get('max', 100))
    tags = request.GET.get('tags', '').strip()
    tags = tags and tags.split(',') or []
    tags = [int(tag) for tag in tags]
    set_focus(request, tags=tags)
    ok = False
    while not ok:
        viewport = [w, s, e, n]
        set_focus(request, key='viewport', value=viewport)
        pois = viewport_get_pois(request, viewport, street_id=street_id, tags=tags)
        n_pois = pois.count()
        ok = n_pois < max_pois
        if not ok:
            divider = n_pois > (max_pois * 2) and 8 or 16
            dy = n-s
            dx = e-w
            n -= dy/divider
            s += dy/divider
            w += dx/divider
            e -= dx/divider
    resource_list_no_sorted = [poi.make_dict(list_item=True) for poi in pois]
    resource_list = sorted(resource_list_no_sorted, key=lambda k: k['name'].lower())
    json_data = json.dumps({'HTTPRESPONSE': 1, 'resource_list': resource_list})
    # return HttpResponse(json_data, mimetype="application/json")
    return HttpResponse(json_data, content_type="application/x-json")

class StreetAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Odonym.objects.all().order_by('name')

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs

class ZoneAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Zone.objects.all().order_by('name')

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs

class PoiAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Poi.objects.all().order_by('name')

        if self.q:
            qs = qs.filter(state=1,name__icontains=self.q)

        return qs

class PoiOkAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Poi.objects.all().order_by('name')

        if self.q:
            qs = qs.filter(state=1,name__icontains=self.q)

        return qs

class TagAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Tag.objects.all().exclude(id=49).order_by('name')

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs

class PoitypeAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Poitype.objects.all().exclude(klass__endswith='0000').exclude(active=False).order_by('name')

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs

class RouteAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Route.objects.all().order_by('name')

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs

class UserAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = User.objects.all().order_by('username')

        if self.q:
            qs = qs.filter(username__icontains=self.q)

        return qs

REGEX_FINDTRAILER = r"(^|\s|'|\"|-)%s"

def search_by_string(request, q, n=None, short=False, pgtrgm=False, what=[], text_in=[], tags=[], live=False):
    if not n:
        n = 100
    zonetypes = [3, 7]
    queries = {}
    l = len(q)
    if l<=2:
        return queries
    if not what or 'resources' in what:
        if pgtrgm:
            pois = Poi.objects.filter(name__similar=q, state=1)
        else:
            pois = Poi.objects.filter(name__iregex=REGEX_FINDTRAILER % q, state=1)
        if tags:
            pois = pois.filter(query_resources_by_tags(tags))
        pois = pois.distinct()
        if live:
            pois = pois.values_list('name', 'slug', 'id')[:n]
        r = pois.count()
        if short or 'short' in text_in:
            if not r:
                if pgtrgm:
                    pois = Poi.objects.filter(short__similar=q, state=1)
                else:
                    pois = Poi.objects.filter(short__iregex=REGEX_FINDTRAILER % q, state=1)
                if tags:
                    pois = pois.filter(query_resources_by_tags(tags))
                pois = pois.distinct()
                if live:
                    pois = pois.values_list('name', 'slug', 'id')[:n]
                    if len(pois) == n:
                        pois = list(pois)
                        pois.append(['...', ''])
            elif r < n:
                pois = list(pois)
                if pgtrgm:
                    more_pois = Poi.objects.filter(short__similar=q, state=1)
                else:
                    more_pois = Poi.objects.filter(short__iregex=REGEX_FINDTRAILER % q, state=1)
                if tags:
                    more_pois = more_pois.filter(query_resources_by_tags(tags))
                more_pois = more_pois.distinct()
                if live:
                    more_pois = more_pois.values_list('name', 'slug', 'id')[:n]
                    poi_ids = [poi[2] for poi in pois]
                    for poi in more_pois:
                        if not poi[2] in poi_ids:
                            pois.append(poi)
                    if len(more_pois) == n:
                        pois.append(['...', ''])
                else:
                    poi_ids = [poi.id for poi in pois]
                    for poi in more_pois:
                        if not poi.id in poi_ids:
                            pois.append(poi)
        if r >= n:
            pois = list(pois)
            if live:
                pois.append(['...', ''])
        if not live:
            pois_no_sorted = [poi.make_dict(list_item=True) for poi in pois]
            pois = sorted(pois_no_sorted, key=lambda k: k['name'].lower())
        queries['pois'] = pois
    if not what or 'categories' in what:
        if pgtrgm:
            categories = Poitype.objects.filter(name__similar=q, poi_poitype__isnull=False)
        else:
            categories = Poitype.objects.filter(name__iregex=REGEX_FINDTRAILER % q, poi_poitype__isnull=False)
        if tags:
            categories = categories.filter(query_categories_by_tags(tags))
        categories = categories.distinct().values_list('name', 'slug')[:n]
        # if categories.count() == n:
        if len(categories) == n: # this patch, required in Django 2, for a bug related to distinct()
            categories = list(categories)
            categories.append(['...', ''])
        queries['categories'] = categories
    if not what or 'zones' in what:
        if q=='via' or (l<= 6 and q.startswith('pia')):
            pass
        else:
            if pgtrgm:
                # MMR 20171107 esclusa ricerca su short
                # zones = Zone.objects.filter( Q(name__similar=q)|Q(short__iregex=REGEX_FINDTRAILER % q), zonetype_id__in=zonetypes).values_list('name', 'slug', 'code')[:n]
                zones = Zone.objects.filter( Q(name__similar=q), zonetype_id__in=zonetypes).values_list('name', 'slug', 'code')[:n]
            else:
                # MMR 20171107 esclusa ricerca su short
                # zones = Zone.objects.filter( Q(name__iregex=REGEX_FINDTRAILER % q)|Q(short__iregex=REGEX_FINDTRAILER % q), zonetype_id__in=zonetypes).values_list('name', 'slug', 'code')[:n]
                zones = Zone.objects.filter( Q(name__iregex=REGEX_FINDTRAILER % q), zonetype_id__in=zonetypes).values_list('name', 'slug', 'code')[:n]

            if zones.count() == n:
            # if len(zones) == n:
                zones = list(zones)
                zones.append(['...', ''])
            queries['zones'] = zones
    if not what or 'streets' in what:
        if q=='via' or (l<= 6 and q.startswith('pia')):
            streets = [['...', '']]
        else:
            if pgtrgm:
                streets = Odonym.objects.filter(name__similar=q, poi_street__isnull=False).distinct().values_list('name', 'slug')[:n]
            else:
                streets = Odonym.objects.filter(name__iregex=REGEX_FINDTRAILER % q, poi_street__isnull=False).distinct().values_list('name', 'slug')[:n]
            if streets.count() == n:
            # if len(streets) == n:
                streets = list(streets)
                streets.append(['...', ''])
        queries['streets'] = streets
    return queries

q_extra = ['(', ')', '[', ']', '"']
def clean_q(q):
    for c in q_extra:
        q = q.replace(c, '')
    return q

def search_all(request):
    if request.method == 'POST': # If the form has been submitted...
        form = PoiSearchForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            q = request.POST.get('q', '')
            q = clean_q(q)
            what = request.POST.getlist('what')
            text_in = request.POST.getlist('text_in')
            tags = request.POST.getlist('tags')
    else:
        what = []
        text_in = ''
        tags = []
        q = request.GET.get('q', '')
        q = clean_q(q)
        if q:
            form = PoiSearchForm(q=q)
        else:
            form = PoiSearchForm()
    queries = search_by_string(request, q, n=100, pgtrgm=False, what=what, text_in=text_in, tags=tags)
    # n_results = len(queries['pois']) + len(queries['categories']) + len(queries['zones']) + len(queries['streets'])
    n_results = len(queries.get('pois', [])) + len(queries.get('categories', [])) + len(queries.get('zones', [])) + len(queries.get('streets', []))
    return render(request, 'pois/search_results.html', {'q': q, 'queries': queries, 'n_results': n_results, 'form': form,})
