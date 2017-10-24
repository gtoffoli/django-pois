// proj_OSM = new OpenLayers.Projection("EPSG:3857");
proj_OSM = new OpenLayers.Projection("EPSG:900913"); // Spherical Mercator Projection - Google Map's modified Mercator projection
proj_ISTAT = new OpenLayers.Projection("EPSG:23032");
proj_GPS = new OpenLayers.Projection("EPSG:4326 "); // WGS 1984 (World Geodetic System)
// OpenLayers.Projection.addTransform("EPSG:900913", "EPSG:3857", "EPSG:23032");

var MAX_ZOOM = 15;
var MIN_ZOOM = 14;

var map, base_layer, vectors;
function getSize(feature) {
     // return size_in_meters / feature.layer.map.getResolution();
     zoom =  feature.layer.map.getZoom();
     return zoom;
}
function show_scale(){
    document.getElementById('feature_log').innerHTML = map.getScale();
}

function on_feature_selected(event){
    // get feature attributes
    attrs = event.feature.attributes;
    url = attrs.url
    // navigate to the feature detail page
    window.location.href = url;
    return true;
}

function add_poi_feature(poi_dict) {
    if (poi_dict['point']) {
        poi = window.geojson_format.read(poi_dict['point'])[0];
        poi.attributes = { id: poi_dict['id'], name: poi_dict['name'], icon_name: poi_dict['icon'], icon_color: poi_dict['color'], url: poi_dict['url'] };
        window.pois.addFeatures(poi);
    }
}

function explore_viewport() {
    $("body").css("cursor","wait");
    if(map.getZoom() < MIN_ZOOM) {
        map.zoomTo(MIN_ZOOM);
    }
    vp = map.getExtent().toArray();
    s = '/set_viewport?left={0}&bottom={1}&right={2}&top={3}';
    url = s.format(vp[0], vp[1], vp[2], vp[3]);
    $.getJSON(url, function (data) {
         $("body").css("cursor","default");
         window.location = '/viewport?from=' + location.pathname;
    })
}

if (!String.prototype.format) {
    String.prototype.format = function() {
        var args = arguments;
        return this.replace(/{(\d+)}/g, function(match, number) { 
            return typeof args[number] != 'undefined'
                        ? args[number]
                    : match
            ;
        });
    };
}

function explore_location(loc) {
    lonLat = new OpenLayers.LonLat(loc.coords.longitude, loc.coords.latitude)
    lonLat.transform(new OpenLayers.Projection("EPSG:4326"), new OpenLayers.Projection("EPSG:900913"));
    y = lonLat.lat;
    x = lonLat.lon;
    s = '/set_viewport?left={0}&bottom={1}&right={2}&top={3}';
    url = s.format(x-DX, y-DY, x+DX, y+DX);
    $.getJSON(url, function (data) {
        window.location = '/viewport?from=' + location.pathname;
    })
}
