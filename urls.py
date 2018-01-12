from __future__ import unicode_literals

# from django.conf.urls.defaults import *
# MMR old version - from django.conf.urls import patterns, include, url
from django.conf.urls import include, url
# MMR added
from pois import views

# Add before admin.autodiscover() and any form import for that matter:
"""
MMR temporaneamente disattivato
import autocomplete_light
autocomplete_light.autodiscover()
"""

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
from django.contrib.gis import admin
admin.autodiscover()

"""
MMR old vesion
urlpatterns = patterns('',
    url(r'^zonetypes$', 'views.zonetype_index'),
    url(r'^zonetype/(?P<zonetype_id>\d+)/$', 'pois.views.zonetype_detail'),
    url(r'^zone$', 'pois.views.zone_index'),
    url(r'^zone/(?P<zone_id>\d+)/$', 'pois.views.zone_detail'),
    url(r'^tags$', 'pois.views.tag_index'),
    url(r'^poitype$', 'pois.views.category_index'), # poitype_index
    url(r'^poitype/(?P<klass>\d+)/$', 'pois.views.poitype_detail'),
    url(r'^$', 'pois.views.poi_index'),
    url(r'^(?P<poi_id>\d+)/$', 'pois.views.poi_detail'),
    url(r'^new$', 'pois.views.poi_new'),
    url(r'^(?P<poi_id>\d+)/edit$', 'pois.views.poi_edit'),
    url(r'^save$', 'pois.views.poi_save'),
    url(r'^poi$', 'pois.views.poi_index'),
    url(r'^poi/(?P<poi_id>\d+)/$', 'pois.views.poi_detail'),
    url(r'^save_note$', 'pois.views.poi_save_note'),
    url(r'^zonize/(?P<poi_id>\d+)/$', 'pois.views.poi_zonize'),
    url(r'^street/(?P<street_id>\d+)/$', 'pois.views.street_detail'),
    url(r'^network/(?P<poi_id>\d+)/$', 'pois.views.poi_network'),
    )
"""
app_name="pois"

urlpatterns = [
    url(r'^zonetypes$', views.zonetype_index),
    url(r'^zonetype/(?P<zonetype_id>\d+)/$', views.zonetype_detail),
    url(r'^zone$', views.zone_index),
    url(r'^zone/(?P<zone_id>\d+)/$', views.zone_detail),
    url(r'^tags$', views.tag_index),
    url(r'^poitype$', views.category_index), # poitype_index
    url(r'^poitype/(?P<klass>\d+)/$', views.poitype_detail),
    url(r'^$', views.poi_index),
    url(r'^(?P<poi_id>\d+)/$', views.poi_detail),
    url(r'^new$', views.poi_new),
    url(r'^(?P<poi_id>\d+)/edit$', views.poi_edit),
    url(r'^save$', views.poi_save),
    url(r'^poi$', views.poi_index),
    url(r'^poi/(?P<poi_id>\d+)/$', views.poi_detail),
    url(r'^save_note$', views.poi_save_note),
    url(r'^zonize/(?P<poi_id>\d+)/$', views.poi_zonize),
    url(r'^street/(?P<street_id>\d+)/$', views.street_detail),
    url(r'^network/(?P<poi_id>\d+)/$', views.poi_network),
    ]