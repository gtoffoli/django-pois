// proj_OSM = new OpenLayers.Projection("EPSG:3857");
proj_OSM = new OpenLayers.Projection("EPSG:900913"); // Spherical Mercator Projection - Google Map's modified Mercator projection
proj_ISTAT = new OpenLayers.Projection("EPSG:23032");
proj_GPS = new OpenLayers.Projection("EPSG:4326 "); // WGS 1984 (World Geodetic System)
// OpenLayers.Projection.addTransform("EPSG:900913", "EPSG:3857", "EPSG:23032");

var MAX_ZOOM = 15;
var MIN_ZOOM = 14;
var cluster_distance = 15;

// MMMR var map, base_layer, vectors;
var map, base_layer, vectors, geojson_format, pois;
/*
MMR
var poi_style = new OpenLayers.Style({
	'fillColor': '#FF0000',
	'fillOpacity': .0, // .2,
	'strokeColor': '${icon_color}',
	'strokeWidth': 1,
	'pointRadius': '${radius}',
	'label': '',
	'labelAlign': 'cm',
	'fontFamily': 'arial',
	'fontSize': '0.5em',
	'graphicName': '${icon_name}',
	},
    { 'context': {
        radius: function(feature) {
            return Math.max(5, 2 * (feature.layer.map.getZoom() - 11));
        }}
    });
*/
var poi_style = new OpenLayers.Style({
    'fillColor': '#77DDFF',
    'fillOpacity': .8, // .2,
    'strokeColor': ' ${color}',
    'strokeWidth': 1,
    'pointRadius': '${radius}',
    'label': '${count}',
    'labelOutlineWidth': 1,
    'fontColor': '#333333',
    'fontSize': '14px',
    'fontWeight': 'bold',
    'graphicName': '${symbol}',
    },
    {'context': 
        {
            radius: function(feature) {
                var radius = Math.max(5, 2 * (feature.layer.map.getZoom() - 8));
                var num = feature.attributes.count || 1;
                if (num>1) return Math.max(radius, Math.min(cluster_distance/2 + 2, radius * Math.sqrt(Math.sqrt(num))));
                else return radius;
            },
            symbol: function(feature) {
                var num = feature.attributes.count || 1;
                if (num>1) return 'circle';
                else return feature.attributes.icon_name;
            },
            color: function(feature) {
                var num = feature.attributes.count || 1;
                if (num>1) return feature.cluster[0].attributes.icon_color;
                else return feature.attributes.icon_color;
            },
            count: function(feature) {
                var num = feature.attributes.count || 1;
                if (num>1) return num;
                else return '';
            }
        }
    }
);
/* MMR
var poi_style_selected = new OpenLayers.Style({
	'fillColor': '#FFFFFF',
	'fillOpacity': 1.0,
	'strokeColor': '${icon_color}',
	'strokeWidth': 2,
	'pointRadius': 10,
	'label': '${name}',
	'labelAlign': 'cm',
	'fontFamily': 'arial',
	'fontSize': '14px',
	'fontOpacity': '1.0',
	'labelBackgroundColor': '#FFFFFF',
	'graphicName': '${icon_name}',
    'cursor': 'pointer',
});
*/
var poi_style_selected = new OpenLayers.Style({
	'strokeWidth': 2,
	'fontSize': '14px',
	'cursor': 'pointer',
});
var poi_style_map = new OpenLayers.StyleMap({
	'default': poi_style,
	'select': poi_style_selected,
});
var zone_style = new OpenLayers.Style({
	'fillColor': '#FF8000', //'#0080FF',
	'fillOpacity': .2,
	'strokeColor': '#777777',
	'strokeWidth': 1,
	'fontColor': '#FFFFFF',
	'fontOpacity': 1.0,
	'label': '${name}',
	'strokeColor': '#333333',
});
var zone_style_map = new OpenLayers.StyleMap({
	'default': zone_style,
});

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
	$("html").addClass("wait");
	if(map.getZoom() < MIN_ZOOM) {
		map.zoomTo(MIN_ZOOM);
	}
	vp = map.getExtent().toArray();
	s = '/set_viewport?left={0}&bottom={1}&right={2}&top={3}';
	url = s.format(vp[0], vp[1], vp[2], vp[3]);

	$.getJSON(url, function (data) {
      console.log('ENTRO JSON');
	  window.location = '/viewport?from=' + location.pathname;
	});
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
	/*
	$.getJSON(url, function (data) {
		window.location = '/viewport?from=' + location.pathname;
	})
	*/
	alert (location.pathname);
	window.location = '/viewport?from=' + location.pathname;
}
