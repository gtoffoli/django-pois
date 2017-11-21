{% extends "gis/admin/openlayers.js" %}
{% block base_layer %}new OpenLayers.Layer.Google("Google Satellite", {type: google.maps.MapTypeId.SATELLITE, numZoomLevels: 22});
    var osm = new OpenLayers.Layer.OSM("OpenStreetMap (Mapnik)");
    {{ module }}.map.addLayer(osm);
    var gmap = new OpenLayers.Layer.Google("Google Streets", { numZoomLevels: 20 });
	{{ module }}.map.addLayer(gmap);
{% endblock %}
