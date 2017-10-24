# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
# Add before admin.autodiscover() and any form import for that matter:
from collections import defaultdict
# MMR old version - from urlparse import urlsplit
from urllib.parse import urlsplit
import json
from django.template.defaultfilters import slugify
"""
MMR temporaneamente disattivato
import autocomplete_light
autocomplete_light.autodiscover()
"""
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, get_object_or_404                    #MMR old version - render_to_response,
from django.template import RequestContext
from django.contrib.gis.shortcuts import render_to_kml
from django.contrib.gis.geos import Polygon, LinearRing
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.flatpages.models import FlatPage
from django.contrib.auth.decorators import login_required
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils.translation import ugettext_lazy as _ 
from django_user_agents.utils import get_user_agent

from django.conf import settings
from roma.session import get_focus, set_focus, focus_set_category, focus_add_themes
from django.db.models.functions import Lower
from pois.models import Zonetype, Zone, Route, Odonym, Poitype, Poi, Tag # MMR temporaneamente disattivato -, Blog
from pois.models import list_all_zones
from pois.models import make_zone_subquery
from pois.models import refresh_configuration
from pois.forms import PoiUserForm, PoiAnnotationForm
from pois.models import MACROZONE, TOPOZONE, MUNICIPIO, CAPZONE
from pois.forms import  PoiBythemeForm, PoiSearchForm # MMR temporaneamente disattivato - BlogUserForm, PostUserForm, TagUserForm,
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
class ZoneAdmin(admin.OSMGeoAdmin):
    pnt = Point(roma_lon, roma_lat, srid=srid_GPS)
    pnt.transform(srid_OSM)
    default_lon, default_lat = pnt.coords
    default_zoom = 13
    list_filter = ('geom',)
    list_display = ('geom',)

def zonetype_index(request):
    # zonetypes = Zonetype.objects.filter(id__in=[0,7,1,3,6]).order_by('name')
    zonetypes = [Zonetype.objects.get(pk=id) for id in [0,7,1,3,4,5,6]]
    zonetype_list = []
    for zt in zonetypes:
        zonetype_list.append([zt, zt.name, Zone.objects.filter(zonetype=zt.pk).count()])
    # MMR old version - return render_to_response('pois/zonetype_index.html', {'zonetype_list': zonetype_list,}, context_instance=RequestContext(request))
    return render(request, 'pois/zonetype_index.html', {'zonetype_list': zonetype_list,})

def zonetype_detail(request, zonetype_id, zonetype=None):
    if not zonetype:
        zonetype = get_object_or_404(Zonetype, pk=zonetype_id)
    zonetype_name = zonetype.name
    zone_list = Zone.objects.filter(zonetype=zonetype_id).exclude(id=90).order_by('id')
    # MMR old version - return render_to_response('pois/zonetype_detail.html', {'zonetype': zonetype, 'zonetype_name': zonetype_name, 'zone_list': zone_list,}, context_instance=RequestContext(request))
    return render(request,'pois/zonetype_detail.html', {'zonetype': zonetype, 'zonetype_name': zonetype_name, 'zone_list': zone_list,})

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
        # zone_list = Zone.objects.filter(zonetype_id__in=[0,7,3,6]).exclude(id=90).order_by('zonetype__name_it', 'id')
        zone_list = Zone.objects.filter(zonetype_id__in=[0,7,3,6]).exclude(id=90).order_by('zonetype__name', 'id')
    # MMR old version - return render_to_response('pois/zone_index.html', {'zonetype': zonetype, 'zonetype_name': zonetype_name, 'zone_list': zone_list,}, context_instance=RequestContext(request))
    return render(request, 'pois/zone_index.html', {'zonetype': zonetype, 'zonetype_name': zonetype_name, 'zone_list': zone_list,})

def zone_index_map(request, zonetype_id=1, prefix='', render_view=True):
    zonetype = get_object_or_404(Zonetype, pk=zonetype_id)
    zonetype_label = ''
    region = 'LAZIO'
    user_agent = get_user_agent(request)
    view_map = user_agent.is_pc or user_agent.is_tablet
    if zonetype_id or zonetype_id==0:
        if zonetype_id==0 and prefix:
            zone_list = Zone.objects.filter(zonetype=zonetype_id, code__istartswith=prefix).exclude(geom__isnull=True).order_by('name')
            zonetype_label = prefix=='RM.' and _('macrozones') or prefix=='PR.' and _('provinces')
            region = prefix=='RM.' and 'ROMA' or prefix=='PR.' and 'LAZIO'
        elif zonetype_id==3 and prefix:
            zone_list = Zone.objects.filter(zonetype=zonetype_id, code__istartswith=prefix).exclude(geom__isnull=True).order_by('name')
            zonetype_label = prefix=='R.' and _('rioni - historical quarters') or prefix=='Q.' and _('quarters') or prefix=='S.' and _('quarter extensions') or prefix=='Z.' and _('suburban zones')
            region = 'ROMA'
        elif zonetype_id==7 and prefix:
            zone_list = Zone.objects.filter(zonetype=zonetype_id, code__istartswith=prefix).exclude(geom__isnull=True)
            zonetype_label = prefix=='M.' and _('municipalities') or prefix=='COM.' and _('towns')
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
    data_dict = {'view_map': view_map, 'zonetype': zonetype, 'zone_list' : zone_list, 'zone_count' : zcount, 'zonetype_label': zonetype_label, 'region': region, 'prefix': prefix}

    if render_view:
        # MMR old version - return render_to_response('pois/zone_index_map.html', data_dict, context_instance=RequestContext(request))
       return render(request, 'pois/zone_index_map.html', data_dict)
    else:
        return data_dict
 
def zone_kml(request, zonetype_id=6):
    if zonetype_id:
        zone_list = Zone.objects.filter(zonetype=zonetype_id)
    else:
        zone_list = Zone.objects.all()
    return render_to_kml("zones.kml", {'zones' : zone_list}) 

def muoviroma(request):
    flatpage = FlatPage.objects.get(url='/help/muoviroma/')
    text_body = flatpage.content
    #MMR old version - return render_to_response('pois/muoviroma.html', {'text_body': text_body}, context_instance=RequestContext(request))
    return render(request, 'pois/muoviroma.html', {'text_body': text_body})

def tag_set(request, tag_id, redirect=True):
    set_focus(request, tags=[tag_id])
    if redirect:
        referer = request.META.get('HTTP_REFERER', None)
        redirect_to = urlsplit(referer, 'http', False)[2]
        return HttpResponseRedirect(redirect_to)

def tag_toggle(request, tag_id, redirect=True):
    # tag_id = int(tag_id)
    focus = get_focus(request)
    tags = focus.get('tags', [])
    print ('TAG_TOGGLE')
    print ('tag_id: ', tag_id)
    print ('focus: ', focus)
    print ('tags: ', tags)
    if tag_id in tags:
        tags.remove(tag_id)
    else:
        tags.append(tag_id)
    set_focus(request, tags=tags)
    print ('focus: ', get_focus(request))
    print ('tags: ', tags)
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

    # compute categories (poitypes) and themes (tags) for all resources in region
    poitypes = Poitype.objects.filter(klass__in=poitype_ids).order_by('klass')
    tags = Tag.objects.filter(Q(poitype__in=poitypes) | Q(poi__in=poi_list)).distinct() # 130729 esteso: OK

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

    # data_dict = {'zone': zone, 'macrozones': macrozones, 'subzone_list': subzone_list, 'tag_list': tag_list, 'poitype_list': poitype_list, 'can_edit': can_edit,}
    data_dict = {'zone': zone, 'macrozones': macrozones, 'subzone_list': subzone_list, 'tag_list': tag_list, 'tag_id': selected_tag, 'poitype_list': poitype_list, 'can_edit': can_edit,}
    if render_view:
        flatpage = FlatPage.objects.get(url='/help/zonemap/')
        data_dict['help'] = flatpage.content
        # MMR old version - return render_to_response('pois/zone_map.html', data_dict, context_instance=RequestContext(request))
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
    language = RequestContext(request).get('LANGUAGE_CODE', 'en')
    # MMR old version cache - streets_cache = get_cache('streets')
    key = 'street_%05d' % street_id
    """
    MMR old version cache
    if not language.startswith('it') or request.GET.get('nocache', None):
        data_dict = None
    else:
        data_dict = streets_cache.get(key, None)
    """
    data_dict = None
    if data_dict:
        print ('%s valid' % key)
    else:
        print ('%s invalid' % key)
        help_text = FlatPage.objects.get(url='/help/street/').content
        # zone_list = [[zone, zone.zonetype.name] for zone in street.get_zones()]
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
        """
        MMMR old version cache
        if language.startswith('it'):
            try:
                streets_cache.set(key, data_dict)
            except:
                print (data_dict)
        """
    can_edit = street.can_edit(request)
    data_dict['can_edit'] = can_edit
    # MMR old version - return render_to_response('pois/street_detail.html', data_dict, context_instance=RequestContext(request))
    return render(request, 'pois/street_detail.html', data_dict)

def street_detail_by_slug(request, street_slug):
    street = get_object_or_404(Odonym, slug=street_slug)
    return street_detail(request, street.id, street)

@xframe_options_exempt
def zone_detail(request, zone_id, zone=None):
    if not zone:
        zone = get_object_or_404(Zone, pk=zone_id)
        return HttpResponseRedirect('/zona/%s/' % zone.slug)
    language = RequestContext(request).get('LANGUAGE_CODE', 'en')
    #MMR old version - zonemaps_cache = get_cache('zonemaps')
    key = 'zone%04d' % zone_id
    """
    MMR old version 
    if not language.startswith('it') or request.GET.get('nocache', None):
        data_dict = None
    else:
        data_dict = zonemaps_cache.get(key, None)
        # print data_dict
    """
    data_dict = None
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
        # zone_dict['neighbouring'] = [z.make_dict(list_item=True) for z in zone.neighbouring()]
        zone_dict['neighbouring'] = zone.neighbouring()
        # zone_dict['overlapping'] = [z.make_dict(list_item=True) for z in zone.overlapping()]
        if zone.zonetype_id == MACROZONE:
            subzone_list = zone.list_subzones(zonetype_id=TOPOZONE)
            print (subzone_list)
        elif zone.zonetype_id in [TOPOZONE, MUNICIPIO]:
            macrozones = Zone.objects.filter(zonetype_id=MACROZONE, zones=zone)
            macrozones = [z.make_dict for z in macrozones]
        # pois = Poi.objects.select_related().filter(zones=zone, state=1).order_by('name')
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
        # initial={'tags': []}
        form = PoiBythemeForm()
        data_dict = {'help': help_text, 'zone': zone_dict, 'macrozones': macrozones, 'subzone_list': subzone_list, 'poi_dict_list': poi_dict_list, 'form': form}
        """
        MMR old version cache
        if language.startswith('it'):
            try:
                zonemaps_cache.set(key, data_dict)
            except:
                pass
                # print data_dict        
        """
    data_dict['can_edit'] = zone.can_edit(request)
    # MMR old version - return render_to_response('pois/zone_detail.html', data_dict, context_instance=RequestContext(request))
    return render(request, 'pois/zone_detail.html', data_dict)

def zone_detail_by_slug(request, zone_slug):
    zone = get_object_or_404(Zone, slug=zone_slug)
    return zone_detail(request, zone.id, zone)

def route_index(request):
    routes = Route.objects.all()
    # MMR old version - return render_to_response('pois/route_index.html', {'routes': routes,}, context_instance=RequestContext(request))
    return render(request, 'pois/route_index.html', {'routes': routes,})

@xframe_options_exempt
def route_detail(request, route_id, route=None):
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
    # MMR old version - return render_to_response('pois/route_detail.html', data_dict, context_instance=RequestContext(request))
    return render(request, 'pois/route_detail.html', data_dict)

def route_detail_by_slug(request, route_slug):
    route = get_object_or_404(Route, slug=route_slug)
    return route_detail(request, route.id, route)

@xframe_options_exempt
def viewport(request):
    help_text = FlatPage.objects.get(url='/help/viewport/').content
    focus = get_focus(request)
    # MMR tags = focus.get('tags', [])
    tags = []
    if request.method == 'POST':
        tags = request.POST.getlist('tags')
    viewport = focus.get('viewport', None)
    if not viewport:
        try:
            """
            MMR old version
            w = float(request.REQUEST['left'])
            s = float(request.REQUEST['bottom'])
            e = float(request.REQUEST['right'])
            n = float(request.REQUEST['top'])
            """
            w = float(request.GET['left'])
            s = float(request.GET['bottom'])
            e = float(request.GET['right'])
            n = float(request.GET['top'])
        except:
            # MMR old version - return render_to_response("roma/slim.html", {'text': '',}, context_instance=RequestContext(request))
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
    # MMR old version - return render_to_response('pois/street_detail.html', {'help': help_text, 'poi_dict_list': poi_dict_list, 'view_type': 'viewport', 'form': form, 'tags': tags,}, context_instance=RequestContext(request))
    return render(request, 'pois/street_detail.html', {'help': help_text, 'poi_dict_list': poi_dict_list, 'view_type': 'viewport', 'form': form, 'tags': tags, 'region': region})

def choose_zone(request):
    help_text = FlatPage.objects.get(url='/help/viewport/').content
    # MMR old version - return render_to_response('pois/choose_zone.html', {'help': help_text}, context_instance=RequestContext(request))
    return render(request, 'pois/choose_zone.html', {'help': help_text})

def zone_cloud(request):
    """ allows to test zone_cloud.html and zone_net """
    code = request.REQUEST['zone']
    zone = Zone.objects.filter(code=code)[0]
    # MMR old version - return render_to_response('pois/zone_cloud.html', {'zone': zone}, context_instance=RequestContext(request))
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
        print (x, y)
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
    print (nodes)
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
    tag_ids = Tag.objects.filter(poitype__klass=in_klass).values_list('id', flat=True)
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
    tag_list = Tag.objects.all().order_by('weight')
    tag_poitype_list = []
    for tag in tag_list:
        tag_id = tag.id
        tag_name = tag.name
        tag_slug = tag.slug
        tag_url = tag.friendly_url
        n_pois, poitype_instances_list = resources_by_tag_and_zone(tag, list_all=list_all)
        if n_pois or list_all:
            tag_poitype_list.append([tag_id, tag_url, tag_name, tag_slug, n_pois, poitype_instances_list])
    # MMR old version - return render_to_response('pois/tag_index.html', {'tag_poitype_list': tag_poitype_list,}, context_instance=RequestContext(request))
    return render(request, 'pois/tag_index.html', {'tag_poitype_list': tag_poitype_list})

@xframe_options_exempt
def zone_tag_index(request, zone_id, zone=None):
    if not zone:
        zone = get_object_or_404(Zone, pk=zone_id)
    language = RequestContext(request).get('LANGUAGE_CODE', 'en')
    # MMR old version cache - zones_cache = get_cache('zones')
    key = 'zone%04d' % zone_id
    """
    MMR old version cache
    if not language.startswith('it') or request.GET.get('nocache', None):
        tag_poitype_list = None
        print ('%s invalid' % key)
    else:
        tag_poitype_list = zones_cache.get(key, None)
        print ('%s valid' % key)
    """
    tag_poitype_list = None
    if not tag_poitype_list:
        tag_list = Tag.objects.all().order_by('weight')
        tag_poitype_list = []
        for tag in tag_list:
            n_pois, poitype_instances_list = resources_by_tag_and_zone(tag, zone=zone, list_all=False)
            if n_pois:
                # tag_poitype_list.append([tag, tag_name, tag_slug, n_pois, poitype_instances_list])
                tag_poitype_list.append([tag.friendly_url(), tag.name, tag.slug, n_pois, poitype_instances_list])
        """
        MMR old version cache
        if language.startswith('it'):
            try:
                zones_cache.set(key, tag_poitype_list)
                pass
            except:
                print (tag_poitype_list)
    cache = get_cache('custom')
    """
    key = 'allzones_' + language
    """
    MMR old version cache
    if request.GET.get('nocache', None):
        all_zones = None
        print ('allzones invalid')
    else:
        all_zones = cache.get(key, None)
        print ('allzones valid')
    """
    all_zones = None
    if not all_zones:
        all_zones = list_all_zones()
        #MMR old version cache - cache.set(key, all_zones)
    can_edit = zone.can_edit(request)
    region = zone.zone_parent()
    zonetype_label = zone.type_label()
    
    # MMR old version - return render_to_response('pois/zone_tag_index.html', {'zone': zone, 'zonetype_list': all_zones, 'tag_poitype_list': tag_poitype_list, 'can_edit': can_edit,}, context_instance=RequestContext(request))
    return render(request, 'pois/zone_tag_index.html', {'zone': zone, 'region': region, 'zonetype_label': zonetype_label, 'zonetype_list': all_zones, 'tag_poitype_list': tag_poitype_list, 'can_edit': can_edit,})


def zone_tag_index_by_slug(request, zone_slug):
    zone = get_object_or_404(Zone, slug=zone_slug)
    return zone_tag_index(request, zone.id, zone=zone)

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
    # MMR return render_to_response('pois/poitype_index.html', {'poitype_instances_list': poitype_instances_list,}, context_instance=RequestContext(request))
    return render(rquest, 'pois/poitype_index.html', {'poitype_instances_list': poitype_instances_list,})

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
    for poitype in poitypes:
        klass = poitype.klass
        if not poitype.active:
            continue
        if klass[4:] == '0000':
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
        print (last_category_poitype)
        category_name = last_category_poitype.name
        category_list.append([last_code, last_category_poitype, category_name, m, poitype_instances_list])
    # MMR old version - return render_to_response('pois/poitype_index.html', {'category_list': category_list,}, context_instance=RequestContext(request))
    return render(request, 'pois/poitype_index.html', {'category_list': category_list,})

@xframe_options_exempt
def tag_detail(request, tag_id, tag=None):
    if not tag:
        tag = get_object_or_404(Tag, pk=tag_id)
    language = RequestContext(request).get('LANGUAGE_CODE', 'en')
    # MMR old version cache - themes_cache = get_cache('themes')
    key = 'theme_%02d' % tag_id
    """
    MMR old version cache
    if not language.startswith(LANGUAGE_CODE) or request.GET.get('nocache', None):
        data_dict = None
    else:
        data_dict = themes_cache.get(key, None)
    """
    data_dict = None
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
        print (n_poitype_list)
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
        """
        MMR old version cache
        if language.startswith(LANGUAGE_CODE):
            try:
                themes_cache.set(key, data_dict)
            except:
                print (data_dict)
        """
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
            # poitype_instances_list.append([poitype, n, category_in_theme])
            poitype_instances_list.append([poitype, n, category_in_theme, pois[:1]])
            n_pois += n
    # MMR old version - return render_to_response('pois/tag_zone_detail.html', {'tag': tag, 'zone': zone, 'poitype_list': poitype_instances_list,}, context_instance=RequestContext(request))
    return render('pois/tag_zone_detail.html', {'tag': tag, 'zone': zone, 'poitype_list': poitype_instances_list,})

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
    language = RequestContext(request).get('LANGUAGE_CODE', 'en')
    # MMR old version cache - categories_cache = get_cache('categories')
    key = 'cat_%s' % klass
    """
    MMR old version cache
    if not language.startswith('it') or request.GET.get('nocache', None) or theme:
        data_dict = []
    else:
        data_dict = categories_cache.get(key, None)
        if data_dict:
            print ('%s valid' % key)
        else:
            print ('%s invalid' % key)
    """
    data_dict = []
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
            # theme_list = poitype.tags.all()
            if poi_list.count() > MAX_POIS and not list_all:
                zones = Zone.objects.filter(zonetype_id=0).exclude(code='ROMA')
                zone_list = zone_list_no_sorted = []
                for zone in zones:
                    pois = resources_by_category_and_zone(klass, zone)
                    if pois:
                        n = pois.count()
                        max_count = max(n, max_count); min_count = min(n, min_count)
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
        poitype = { 'name': poitype.name,  'slug': poitype.slug, 'active': poitype.active }
        if sub_types:
            poitype['sub_types'] = sub_types
        data_dict = {'help': help_text, 'poitype': poitype, 'theme_list': theme_list, 'poi_dict_list': poi_dict_list, 'region': region, 'zone_list': zone_list, 'min': min_count, 'max': max_count}
        data_dict['zone'] = zone
        """
        MMR old version cache
        if language.startswith('it') and not theme:
            try:
                categories_cache.set(key, data_dict)
            except:
                print (data_dict)
        """
    # MMR old version return render_to_response('pois/poitype_detail.html', data_dict, context_instance=RequestContext(request))
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
    # MMR old version - return render_to_response('pois/poitype_detail.html', data, context_instance=RequestContext(request))
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
    language = RequestContext(request).get('LANGUAGE_CODE', 'en')
    # MMR old version version - catzones_cache = get_cache('catzones')
    key = 'cat_%s_zone%04d' % (klass, zone_id)
    region = 'ROMA'
    """
    MMR old version cache
    if not language.startswith('it') or request.GET.get('nocache', None):
        data_dict = None
    else:
        data_dict = catzones_cache.get(key, None)
    """
    data_dict = None
    if data_dict:
        print ('%s valid' % key)
    else:
        print ('%s invalid' % key)
        poi_list = resources_by_category_and_zone(klass, zone, select_related=True)
        zone_list = zone_list_no_sorted = []
        print(zone.zonetype_id)
        print(zone.id)
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

        """
        MMR old version cache
        if language.startswith('it'):
            try:
                catzones_cache.set(key, data_dict)
            except:
                print (data_dict)
        """
    data_dict['zone'] = zone
    # MMR old version - return render_to_response('pois/poitype_detail.html', data_dict, context_instance=RequestContext(request))
    return render(request, 'pois/poitype_zone_detail.html', data_dict)

def poitype_zone_detail_by_slugs(request, klass_slug, zone_slug):
    poitype = get_object_or_404(Poitype, slug=klass_slug)
    zone = get_object_or_404(Zone, slug=zone_slug)
    return poitype_zone_detail(request, poitype.klass, zone.id, poitype=poitype, zone=zone)

def poi_index(request):
    poi_list = Poi.objects.all()
    #MMR old version - return render_to_response('pois/poi_index.html', {'poi_list': poi_list,}, context_instance=RequestContext(request))
    return render(request, 'pois/poi_index.html', {'poi_list': poi_list,})

# MMR old version  from django.core.cache import get_cache
from django.core.cache import caches

@xframe_options_exempt
def poi_detail(request, poi_id, poi=None):
    if not poi:
        poi = get_object_or_404(Poi, pk=poi_id)
        return HttpResponseRedirect('/risorsa/%s/' % poi.slug)
    language = RequestContext(request).get('LANGUAGE_CODE', 'en')
    can_edit = poi.can_edit(request)
    focus_set_category(request, poi.poitype_id)
    """
    focus_add_themes(request, poi.get_themes_indirect(return_ids=True))
    focus_add_themes(request, poi.get_themes(return_ids=True))
    """
    user_agent = get_user_agent(request)
    # MMR old version cache - pois_cache = get_cache('pois')
    key = 'poi%05d' % poi_id
    """
    MMR old version cache
    if not language.startswith('it') or request.GET.get('nocache', None):
        data_dict = None
    else:
        data_dict = pois_cache.get(key, None)
    """
    data_dict = None
    if not data_dict:
        print ('invalid cache for ', key)
        poi_dict = poi.make_dict() # 140603
        """
        zone_list = Zone.objects.filter(pois=poi_id, zonetype__id__in=[0,7,1,3]).order_by('-zonetype__id', 'id')
        zone_list = [{ 'name': zone.name_with_code(), 'url': zone.friendly_url()} for zone in zone_list]
        """
        zones = Zone.objects.filter(pois=poi_id, zonetype__id__in=[3,7]).order_by('zonetype__id')
        zone_list = []
        macrozone = None
        zone_parent = None
        for zone in zones:
            if zone.zonetype_id == 3: # zona toponomastica
                zone_list.append({ 'name': '%s %s' % (zone.code, zone.name), 'url': '/zona/%s/' % zone.slug, 'slug': zone.slug})
            else: # municipio
                zone_list.append({ 'name': zone.name, 'url': '/zona/%s/' % zone.slug, 'slug': zone.slug})
                zone_parent = zone.zone_parent()
                macrozone = zone.get_macrozone_slug()
        poi_dict['zone_parent'] = zone_parent
        hosted_list = Poi.objects.filter(host=poi).order_by('name')
        hosted_list = [{ 'name': p.name, 'url': p.friendly_url()} for p in hosted_list]
        poi_list = Poi.objects.filter(pois=poi).order_by('name')
        poi_list = [{ 'name': p.name, 'url': p.friendly_url()} for p in poi_list]
        n_caredby = Poi.objects.filter(careof=poi).count()
        poitype = poi.poitype
        if poitype:
            """
            poitype = { 'name': poitype.name, 'url': poitype.friendly_url()}
            """
            if macrozone:
                poitype = { 'name': poitype.name, 'url': '/categoria/%s/zona/%s/' % (poitype.slug, macrozone)}
            else:
                poitype = { 'name': poitype.name, 'url': poitype.friendly_url()}
        theme_list = [{ 'id': theme.id, 'name': theme.name, 'slug': theme.slug } for theme in poi.get_all_themes()]
        data_dict = {'poi_dict': poi_dict, 'poitype': poitype, 'theme_list': theme_list, 'hosted_list': hosted_list, 'zone_list': zone_list, 'poi_list': poi_list, 'n_caredby': n_caredby,}
        if macrozone:
            data_dict['macrozone'] = macrozone
        """
        MMR old version cache
        if language.startswith('it'):
            pois_cache.set(key, data_dict)
        """
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
    # MMR old version - return render_to_response('pois/poi_detail.html', data_dict, context_instance=RequestContext(request))
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
    create_option = []
    results = []
    if q and len(q) >= MIN_CHARS:
        qs = Odonym.objects.filter(name__icontains=q).order_by('name')
        results = [{'id': street.id, 'text': street.name} for street in qs]
    body = json.dumps({'results': results, 'pagination': {'more': False}})
    return HttpResponse(body, content_type='application/json')
    
def poi_edit(request, poi_id):
    poi = get_object_or_404(Poi, pk=poi_id)
    form = PoiUserForm(instance=poi)
    # MMR old version - return render_to_response('pois/poi_edit.html', {'poi': poi, 'form': form}, context_instance=RequestContext(request))
    return (request, 'pois/poi_edit.html', {'poi': poi, 'form': form})

def poi_new(request):
    flatpage = FlatPage.objects.get(url='/risorse/segnala/')
    text_body = flatpage.content
    form = PoiUserForm()
    # MMR old version - return render_to_response('pois/poi_edit.html', {'poi': '', 'form': form, 'text_body': text_body}, context_instance=RequestContext(request))
    return render(request, 'pois/poi_edit.html', {'poi': '', 'form': form, 'text_body': text_body})

def poi_save(request):
    flatpage = FlatPage.objects.get(url='/risorse/segnala/')
    text_body = flatpage.content
    if request.POST:
        form = PoiUserForm(request.POST)
        if form.is_valid():
            # human = True
            poi = form.save()
            if request.user.is_authenticated():
                poi.owner = request.user
                poi.save()
            return HttpResponseRedirect('/nuova-risorsa/%s/' % poi.id)
        else:
            # MMR old version - return render_to_response('pois/poi_edit.html', {'form': form, 'text_body': text_body}, context_instance=RequestContext(request))
            return render(request, 'pois/poi_edit.html', {'form': form, 'text_body': text_body})
    else:
        return poi_new(request)

def poi_view(request,poi_id):
    poi = get_object_or_404(Poi, pk=poi_id)
    flatpage = FlatPage.objects.get(url='/risorse/riscontro/')
    text_body = flatpage.content
    # MMR old version - return render_to_response('pois/poi_view.html', {'poi': poi, 'text_body': text_body}, context_instance=RequestContext(request))
    return render(request, 'pois/poi_view.html', {'poi': poi, 'text_body': text_body})

def poi_add_note(request, poi_id, poi=None):
    flatpage = FlatPage.objects.get(url='/risorsa/annota/')
    text_body = flatpage.content
    if not poi:
        poi = get_object_or_404(Poi, pk=poi_id)
    form = PoiAnnotationForm(initial={'id': poi_id})
    # MMR old version - return render_to_response('pois/poi_feedback.html', {'poi': poi, 'form': form, 'text_body': text_body}, context_instance=RequestContext(request))
    return render(request, 'pois/poi_feedback.html', {'poi': poi, 'form': form, 'text_body': text_body})

def poi_add_note_by_slug(request, poi_slug):
    poi = get_object_or_404(Poi, slug=poi_slug)
    return poi_add_note(request, poi.id, poi=poi)

def poi_save_note(request):
    poi_id = int(request.POST.get('id', 0))
    poi = get_object_or_404(Poi, pk=poi_id)
    form = PoiAnnotationForm(request.POST)
    if form.is_valid():
        now = datetime.datetime.now()
        comment = request.POST['notes']
        poi.notes = """----- commento in data %s -----
%s
-----
%s""" % (now, comment, poi.notes)
        poi.save()
        return HttpResponseRedirect('/risorsa/%s/?comment=true' % poi.slug)
    else:
        # MMR old version - return render_to_response('pois/poi_feedback.html', {'form': form}, context_instance=RequestContext(request))
        return render(request, 'pois/poi_feedback.html', {'form': form})

def pois_recent(request, n=MAX_POIS):
    # instances = Poi.objects.filter(state=1).order_by('-id')[:n]
    instances = Poi.objects.select_related().filter(state=1).order_by('-id')[:n]
    poi_dict_list = [poi.make_dict() for poi in instances]
    # MMR old version - return render_to_response('pois/poi_list.html', {'list_type': 'recent', 'poi_dict_list': poi_dict_list, 'count': instances.count()}, context_instance=RequestContext(request))
    return render(request, 'pois/poi_list.html', {'list_type': 'recent', 'poi_dict_list': poi_dict_list, 'count': instances.count()})

def pois_updates(request, n=MAX_POIS):
    last_id = Poi.objects.latest('id').id
    instances = Poi.objects.select_related().filter(id__lt=last_id-MAX_POIS, state=1).order_by('-modified')[:n]
    poi_dict_list = [poi.make_dict() for poi in instances]
    # MMR old version - return render_to_response('pois/poi_list.html', {'list_type': 'updates', 'poi_dict_list': poi_dict_list, 'count': instances.count()}, context_instance=RequestContext(request))
    return render(request, 'pois/poi_list.html', {'list_type': 'updates', 'poi_dict_list': poi_dict_list, 'count': instances.count()})

def my_resources(request, n=MAX_POIS):
    n = request.GET.get('n', n)
    n = int(n)
    poi_dict_list = []
    count = 0
    if request.user.is_authenticated():
        instances = Poi.objects.filter(owner=request.user).order_by('-id')[:n]
        count = instances.count()
        poi_dict_list = [poi.make_dict() for poi in instances]
    # MMR old version - return render_to_response('pois/poi_list.html', {'list_type': 'my_resources', 'poi_dict_list': poi_dict_list, 'count': count}, context_instance=RequestContext(request))
    return render(request, 'pois/poi_list.html', {'list_type': 'my_resources', 'poi_dict_list': poi_dict_list, 'count': count})

def poi_contributors(request):
    users = User.objects.annotate(num_pois=Count('poi_owner')).filter(num_pois__gt=0).order_by('-num_pois')
    # MMR old version - return render_to_response('pois/poi_contributors.html', { 'user_list': users, }, context_instance=RequestContext(request))
    return render(request, 'pois/poi_contributors.html', { 'user_list': users, })

def poi_zonize(request, poi_id):
    poi = get_object_or_404(Poi, pk=poi_id)
    poi.update_zones(zonetypes=[1, 3, 7])
    return HttpResponseRedirect('/admin/pois/poi/%s/' % poi_id)

def pois_update_colocations(request):
    pois = Poi.objects.exclude(host__isnull=True)
    n = 0
    for poi in pois:
        host = poi.host
        if poi.point == host.point:
            # print poi.name
            pass
        else:
            # print poi.name, '-> ', host.name
            poi.point = host.point
            poi.save()
            n += 1
    html = u"""
<html><body>
<div>Aggiornato la posizione di %d risorse con quella della risorsa ospitante.
</body></html>
""" % n
    return HttpResponse(html, content_type='text/html')

def poi_analysis(request):
    list_all = request.GET.get('all', '')
    no_geo_list = []
    no_theme_list = []
    todo_list = []
    comment_list = []
    notes_list = []
    if list_all or request.GET.get('geo', ''):
        no_geo_list = [poi.make_dict() for poi in Poi.objects.filter(point__isnull=True)]
    if list_all or request.GET.get('theme', ''):
        no_theme_list = [poi.make_dict() for poi in Poi.objects.filter(tags__isnull=True, poitype__tags__isnull=True)]
    if list_all or request.GET.get('todo', '') or request.GET.get('comment', '') or request.GET.get('notes', ''):
        poi_list = Poi.objects.exclude(notes='').exclude(notes__isnull=True)
    if list_all or request.GET.get('todo', ''):
        for poi in poi_list:
            notes = poi.notes
            if notes[0] != '\r' and notes[0] != '\n':
                todo = notes.split('\n')[0]
                item = poi.make_dict()
                item.update({'notes': todo})
                todo_list.append(item)
    if list_all or request.GET.get('comment', ''):
        for poi in poi_list:
            notes = poi.notes
            if notes.count('----- commento'):
                item = poi.make_dict()
                item.update({'notes': notes})
                comment_list.append(item)
    if request.GET.get('notes', ''):
        for poi in poi_list:
            notes = poi.notes
            if notes:
                item = poi.make_dict()
                item.update({'notes': notes})
                notes_list.append(item)
    # MMR old version - return render_to_response('pois/poi_analysis.html', {'no_geo_list': no_geo_list, 'no_theme_list': no_theme_list, 'todo_list': todo_list, 'comment_list': comment_list, 'notes_list': notes_list,}, context_instance=RequestContext(request))
    return render(request, 'pois/poi_analysis.html', {'no_geo_list': no_geo_list, 'no_theme_list': no_theme_list, 'todo_list': todo_list, 'comment_list': comment_list, 'notes_list': notes_list,})

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
    zone_list = []
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
                zone.count = n
                zone.url = '/rete/%s/zona/%s/' % (poi.slug, zone.slug)
                zone_list.append(zone)
        zone = None
        help_text = FlatPage.objects.get(url='/help/big-list/').content
    else:
        poi_dict_list = [poi.make_dict(list_item=True) for poi in poi_list]
    region = 'ROMA'
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
    # MMR old version - return render_to_response('pois/network_detail.html', {'relation': 'affiliated', 'help': help_text, 'zone': zone, 'parent': parent, 'poi_dict_list': poi_dict_list, 'zone_list': zone_list, 'min': min_count, 'max': max_count,}, context_instance=RequestContext(request))
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
    region = zone.zone_parent()
    if poi_dict_list:
        for item in poi_dict_list:
            if item['comune'][1] != 'roma':
                region = 'LAZIO' 
                break
    # MMR old version - return render_to_response('pois/network_detail.html', {'relation': 'affiliated', 'help': help_text, 'parent': parent, 'zone': zone, 'poi_dict_list': poi_dict_list,}, context_instance=RequestContext(request))
    return render(request, 'pois/network_detail.html', {'relation': 'affiliated', 'help': help_text, 'parent': parent, 'zone': zone, 'poi_dict_list': poi_dict_list, 'region': region})

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
    # MMR old version - return render_to_response('pois/network_detail.html', {'relation': 'caredby', 'help': help_text, 'zone': zone, 'parent': parent, 'poi_dict_list': poi_dict_list,}, context_instance=RequestContext(request))
    return render(request, 'pois/network_detail.html', {'relation': 'caredby', 'help': help_text, 'zone': zone, 'parent': parent, 'poi_dict_list': poi_dict_list,})

def resource_map_by_slug(request, poi_slug):
    poi = get_object_or_404(Poi, slug=poi_slug)
    return resource_map(request, poi.id, poi)

from django.db.models import Count
def resource_networks(request):
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
    # MMR old version - return render_to_response('pois/poi_list.html', {'list_type': 'networks', 'poi_dict_list': poi_dict_list, 'count': len(poi_dict_list)}, context_instance=RequestContext(request))
    return render(request, 'pois/poi_list.html', {'list_type': 'networks', 'poi_dict_list': poi_dict_list, 'count': len(poi_dict_list)})

"""
from pois.models import PoiPoi

def resource_networks(request):

    if POI_CLASSES:
        pois = Poi.objects.filter(poitype_id__in=POI_CLASSES, state=1).exclude(state__poi=0)
    else:
        pois = Poi.objects.filter(state=1).exclude(poi__pois=None)

    pois = pois.annotate(num_pois=Count('poipoi')).order_by('-num_pois')

    poi_dict_list = []
    for poi in pois:
        poi_dict = poi.make_dict(list_item=True)
        
        if poi.num_pois > 3:
            poi_dict['num_pois'] = poi.num_pois
            poi_dict_list.append(poi_dict)

    return render_to_response('pois/poi_list.html', {'list_type': 'networks', 'poi_dict_list': poi_dict_list, 'count': len(poi_dict_list)}, context_instance=RequestContext(request))
"""

def resource_maps(request):
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
    # MMR old version - return render_to_response('pois/poi_list.html', {'list_type': 'maps', 'poi_dict_list': poi_dict_list, 'count': len(poi_dict_list)}, context_instance=RequestContext(request))
    return render(request, 'pois/poi_list.html', {'list_type': 'maps', 'poi_dict_list': poi_dict_list, 'count': len(poi_dict_list)})

def viewport_get_pois(request, viewport, street_id=None, tags=[]):
    w, s, e, n = viewport
    geom = Polygon(LinearRing([Point(w, n), Point(e, n), Point(e, s), Point(w, s), Point(w, n)]))
    geom.set_srid(srid_OSM)
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
    """
    w = float(request.REQUEST['left'])
    s = float(request.REQUEST['bottom'])
    e = float(request.REQUEST['right'])
    n = float(request.REQUEST['top'])
    """
    w = float(request.GET['left'])
    s = float(request.GET['bottom'])
    e = float(request.GET['right'])
    n = float(request.GET['top'])
    viewport = [w, s, e, n]
    set_focus(request, key='viewport', value=viewport)
    # return HttpResponse('', mimetype="application/json")
    # MMR 20170910 return HttpResponse('', content_type="application/x-json")
    json_data = json.dumps({'HTTPRESPONSE': 1, 'data': ''})
    return HttpResponse(json_data, content_type="application/x-json")


# riporta le risorse interne alla viewport specificata dalla querystring
def viewport_pois(request):
    """
    w = float(request.REQUEST['left'])
    s = float(request.REQUEST['bottom'])
    e = float(request.REQUEST['right'])
    n = float(request.REQUEST['top'])
    """
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
    
"""
MMR temporaneamente disattivato
def blogs_index(request):
    blog_list = Blog.objects.filter(state=1)
    try:
        text = FlatPage.objects.get(url='/community/blogs/').content
    except:
        text = ''
    return render_to_response('richtext_blog/blog_index.html', {'text': text, 'blog_list': blog_list,}, context_instance=RequestContext(request))

def blog_detail(request, blog_id):
    blog = Blog.objects.get(pk=blog_id)
    can_edit = blog.can_edit(request)
    return render_to_response('richtext_blog/blog_detail.html', {'blog': blog, 'can_edit': can_edit,}, context_instance=RequestContext(request))

def blog_detail_by_slug(request, blog_slug):
    blog = get_object_or_404(Blog, slug=blog_slug)
    return blog_detail(request, blog.id)

def blog_posts(request, blog_id):
    blog = Blog.objects.get(pk=blog_id)
    can_edit = blog.can_edit(request)
    posts = blog.posts()
    return render_to_response('richtext_blog/post-list.html', {'blog': blog, 'post_list': posts, 'can_edit': can_edit,}, context_instance=RequestContext(request))

def blog_posts_by_slug(request, blog_slug):
    blog = get_object_or_404(Blog, slug=blog_slug)
    return blog_posts(request, blog.id)

from richtext_blog.models import Post, Comment
from richtext_blog.views import (PostListView, AllPostsRssFeed, PostView)

def item_blog(self, item):
    return item.get_absolute_url()
AllPostsRssFeed.item_blog = item_blog

def post_view_get_context_data(self, **kwargs):
    print ('post_view_get_context_data')
    # MMR ini commento
    # Define required class attribute for DetailView functionality then pass
    # it into the context along with any comments for the post
    #  fine commento
    # From detail.DetailView.get (called just before get_context_data, so
    # we need the line here)
    self.object = self.get_object()

    # Call the parent get_context_data (in this case it will be the one
    # defined in exit.ProcessFormView)
    context = super(PostView, self).get_context_data(**kwargs)
    context['object'] = self.object
    context['comments'] = \
        Comment.objects.filter(post=self.object).order_by('created')
    print ('post : ', self.object)
    context['can_edit_post'] = self.object.can_edit(self.request)
    return context
PostView.get_context_data = post_view_get_context_data

def get_queryset(self):
    # MMR ini commento
    # Return posts based on a particular blog, year and month. 
    # fine commento
    if 'blog' in self.kwargs:
        objects = Post.objects.filter(blog=self.kwargs['blog'])
        print ('blog = ', self.kwargs['blog'])
    else:
        objects = Post.objects.all()
    if 'month' in self.kwargs:
        objects = objects.filter(created__year=self.kwargs['year'],
            created__month=self.kwargs['month'])
    elif 'year' in self.kwargs:
        objects = objects.filter(created__year=self.kwargs['year'])
    return objects.order_by('-created')
PostListView.get_queryset = get_queryset

def blog_edit(request, blog_slug):
    print (blog_slug)
    blog = get_object_or_404(Blog, slug=blog_slug)
    if not blog.can_edit(request):
        return HttpResponseRedirect(blog.friendly_url())        
    form = BlogUserForm(instance=blog)
    return render_to_response('richtext_blog/blog_edit.html', {'blog': blog, 'form': form,}, context_instance=RequestContext(request))

def blog_save(request):
    blog_id = request.POST['id']
    blog = get_object_or_404(Blog, id=blog_id)
    if not blog.can_edit(request):
        return HttpResponseRedirect(blog.friendly_url())        
    blog.title = request.POST['title']
    blog.description = request.POST['description']
    blog.save()
    return HttpResponseRedirect(blog.friendly_url())

def post_new(request, blog_slug):
    blog = get_object_or_404(Blog, slug=blog_slug)
    if not blog.can_post(request):
        return HttpResponseRedirect(blog.friendly_url())        
    form = PostUserForm(blog_id=blog.id)
    return render_to_response('richtext_blog/post_edit.html', {'blog': blog, 'post': '', 'form': form}, context_instance=RequestContext(request))

def post_edit(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)
    blog = post.blog
    if not post.can_edit(request):
        return HttpResponseRedirect(blog.friendly_url())        
    form = PostUserForm(instance=post)
    return render_to_response('richtext_blog/post_edit.html', {'blog': blog, 'post': post, 'form': form,}, context_instance=RequestContext(request))

def post_save(request):
    form = PostUserForm(request.POST)
    blog = None
    post = None
    if form.is_valid():
        print (form.cleaned_data)
        # post = form.save()
        post_id = form.cleaned_data.get('id')
        if post_id:
            post = get_object_or_404(Post, id=post_id)
            created = post.created
        print ('post_id = ', post_id)
        post = form.save(commit=False)
        if post_id:
            post.id = post_id
            post.created = created
        post.author = request.user
        post.save()
        form.save_m2m()
        return HttpResponseRedirect(post.get_absolute_url())
    else:
        print (form.cleaned_data)
        post_id = form.cleaned_data.get('id')
        if post_id:
            post = get_object_or_404(Post, id=post_id)
            blog = get_object_or_404(Blog, id=post.blog.id)
        return render_to_response('richtext_blog/post_edit.html', {'blog': blog, 'post': post, 'form': form}, context_instance=RequestContext(request))

from django.utils.html import escape
from django import forms
# see http://www.hoboes.com/Mimsy/hacks/replicating-djangos-admin/
# (Replicating Django’s admin form pop-ups)
def handlePopAdd(request, addForm, field):
    if request.method == "POST":
        form = addForm(request.POST)
        if form.is_valid():
            try:
                newObject = form.save()
            except (forms.ValidationError, error):
                newObject = None
            if newObject:
                return HttpResponse('<script type="text/javascript">opener.dismissAddAnotherPopup(window, "%s", "%s");</script>' % \
                    (escape(newObject._get_pk_val()), escape(newObject)))
    else:
        form = addForm()
    pageContext = {'form': form, 'field': field}
    return render_to_response("richtext_blog/add_popup.html", pageContext, context_instance=RequestContext(request))

@login_required
def newTag(request):
    return handlePopAdd(request, TagUserForm, 'tags')
"""

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
            pois = [poi.make_dict(list_item=True) for poi in pois]
        queries['pois'] = pois
    if not what or 'categories' in what:
        if pgtrgm:
            categories = Poitype.objects.filter(name__similar=q, poi_poitype__isnull=False)
        else:
            categories = Poitype.objects.filter(name__iregex=REGEX_FINDTRAILER % q, poi_poitype__isnull=False)
        if tags:
            categories = categories.filter(query_categories_by_tags(tags))
        categories = categories.distinct().values_list('name', 'slug')[:n]
        # if len(categories) == n:
        if categories.count() == n:
            categories = list(categories)
            categories.append(['...', ''])
        queries['categories'] = categories
    if not what or 'zones' in what:
        if q=='via' or (l<= 6 and q.startswith('pia')):
            pass
        else:
            if pgtrgm:
                zones = Zone.objects.filter( Q(name__similar=q)|Q(short__iregex=REGEX_FINDTRAILER % q), zonetype_id__in=zonetypes).values_list('name', 'slug', 'code')[:n]
            else:
                zones = Zone.objects.filter( Q(name__iregex=REGEX_FINDTRAILER % q)|Q(short__iregex=REGEX_FINDTRAILER % q), zonetype_id__in=zonetypes).values_list('name', 'slug', 'code')[:n]
            # if len(zones) == n:
            if zones.count() == n:
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
            # if len(streets) == n:
            if streets.count() == n:
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
    return render_to_response('pois/search_results.html', {'q': q, 'queries': queries, 'form': form,}, context_instance=RequestContext(request))

def navigation_autocomplete(request, template_name='pois/autocomplete.html'):
    zonetypes = [3, 7]
    """
    site_url = request.META.get('HTTP_HOST', 'www.romapaese.it')
    USE_PGTRGM = site_url != settings.ONLINE_DOMAIN
    print site_url, 'USE_PGTRGM = ', USE_PGTRGM
    """
    q = request.GET.get('q', '')
    q = clean_q(q)
    USE_PGTRGM = False
    context = {'q': q}
    l = len(q)

    if settings.USE_HAYSTACK:
        try:
            from haystack.query import SearchQuerySet
            MAX = 16
            results = SearchQuerySet().filter(text=q)
            # return render(request, 'pois/autocomplete_hs.html', {'q': q, 'results': results[:MAX], 'more': results.count()>MAX})
            if results.count()>MAX:
                results = results[:MAX]
                context['more'] = True
            queries = defaultdict(list)
            for result in results:
                klass = result.model.__name__
                values_list = [result.get_stored_fields()['name'], result.get_stored_fields()['slug']]
                if klass=="Zone":
                    values_list.append(result.object.code)
                queries[klass].append(values_list)
            # template_name='pois/autocomplete.html'
        except:
            queries = {}
    # if l>2:
    else:
        MAX = 10
        n = MAX
        queries = {}
        if USE_PGTRGM:
            pois = Poi.objects.filter(name__similar=q, state=1).values_list('name', 'slug', 'id')[:n]
        else:
            pois = Poi.objects.filter(name__iregex=REGEX_FINDTRAILER % q, state=1).values_list('name', 'slug', 'id')[:n]
        r = pois.count()
        if r >= n:
            pois = list(pois)
            pois.append(['...', ''])
        queries['Poi'] = pois
        if USE_PGTRGM:
            categories = Poitype.objects.filter(name__similar=q, poi_poitype__isnull=False).distinct().values_list('name', 'slug')[:n]
        else:
            categories = Poitype.objects.filter(name__iregex=REGEX_FINDTRAILER % q, poi_poitype__isnull=False).distinct().values_list('name', 'slug')[:n]
        # if len(categories) == n:
        if categories.count() == n:
            categories = list(categories)
            categories.append(['...', ''])
        queries['Poitype'] = categories

        if q=='via' or (l<= 6 and q.startswith('pia')):
            pass
        else:
            if USE_PGTRGM:
                zones = Zone.objects.filter( Q(name__similar=q)|Q(short__iregex=REGEX_FINDTRAILER % q), zonetype_id__in=zonetypes).values_list('name', 'slug', 'code')[:n]
            else:
                zones = Zone.objects.filter( Q(name__iregex=REGEX_FINDTRAILER % q)|Q(short__iregex=r"(^|\s|')%s" % q), zonetype_id__in=zonetypes).values_list('name', 'slug', 'code')[:n]
            # if len(zones) == n:
            if zones.count() == n:
                zones = list(zones)
                zones.append(['...', ''])
            queries['Zone'] = zones
 
        if q=='via' or (l<= 6 and q.startswith('pia')):
            streets = [['...', '']]
        else:
            if USE_PGTRGM:
                streets = Odonym.objects.filter(name__similar=q, poi_street__isnull=False).distinct().values_list('name', 'slug')[:n]
            else:
                streets = Odonym.objects.filter(name__iregex=REGEX_FINDTRAILER % q, poi_street__isnull=False).distinct().values_list('name', 'slug')[:n]
            # if len(streets) == n:
            if streets.count() == n:
                streets = list(streets)
                streets.append(['...', ''])
        queries['Odonym'] = streets
        
    context.update(queries)
    return render(request, template_name, context)
    