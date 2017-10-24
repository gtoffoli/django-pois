from __future__ import unicode_literals

from django import forms
from django.conf import settings
from django.utils.safestring import mark_safe

class GoogleMapsWidget(forms.HiddenInput):

    class Media:
        js = (
            'http://ajax.googleapis.com/ajax/libs/django.jQuery/1.4.2/django.jQuery.min.js',
        )

    def render(self, name, value, attrs=None, choices=()):
        # self.attrs['base_point'] = self.attrs.get('base_point', u'42.697649,23.322154')
        self.attrs['base_point'] = self.attrs.get('base_point', '')
        self.attrs['width'] = self.attrs.get('width', 400)
        self.attrs['height'] = self.attrs.get('height', 400)
        # self.attrs['country_city'] = self.attrs.get('country_city', u'Sofia, Bulgaria')
        self.attrs['country_city'] = self.attrs.get('country_city', '')
       
        maps_html = "
            <script type="text/javascript" src="http://maps.google.com/maps/api/js?sensor=true"></script>
            <script type="text/javascript">
                var base_point = new google.maps.LatLng(%(base_point)s);
                django.jQuery(document).ready(function(){
                    if(django.jQuery('#%(latitude)s').val()!=''){
                        center = new google.maps.LatLng(django.jQuery('#%(latitude)s').val(), django.jQuery('#%(longitude)s').val());
                    }else{
                        center = base_point
                    }
                    var myOptions = {
                        zoom: 15,
                        center: center,
                        mapTypeId: google.maps.MapTypeId.ROADMAP
                    };
                    map = new google.maps.Map(document.getElementById("map_canvas"), myOptions);
                    geocoder = new google.maps.Geocoder();
                    my_point = new google.maps.Marker({
                        position: center,
                        map: map,
                        draggable: true,
                    })
                   
                    google.maps.event.addListener(my_point, 'dragend', function(event){
                        django.jQuery('#%(latitude)s').val(event.latLng.lat());
                        django.jQuery('#%(longitude)s').val(event.latLng.lng());
                    });
                    // django.jQuery('#%(longitude)s').parent().parent().hide();
                });
               
                function codeAddress(){
                    var address = django.jQuery('#address').val() + ', ' + django.jQuery('#city_country').val();
                    geocoder.geocode( { 'address': address}, function(results, status) {
                        if (status == google.maps.GeocoderStatus.OK) {
                            results_len = results.length
                            var results_table = new Array();
                            for(i=0; i<results_len; i++){
                                address_location = results[i].geometry.location
                                if(i==0){
                                    set_center(address_location.lat(), address_location.lng())
                                }
                                results_table[i] = '<div style="cursor: pointer" onclick="set_center(' +
                                    address_location.lat() + ', ' +
                                    address_location.lng() + ')">' +
                                    results[i].formatted_address +
                                    '</div>';
                            }
                            django.jQuery('#search_results').html(results_table.join(''));
                        } else {
                            alert("Geocode was not successful for the following reason: " + status);
                        }
                    });
                }
               
                function set_center(lat, lng){
                    latlng = new google.maps.LatLng(lat, lng);
                    my_point.setPosition(latlng)
                    map.setCenter(latlng);
                }
               
                function reset_point(loc){
                    my_point.setPosition(loc)
                    map.setCenter(loc)
                }
            </script>
            <div id="map_canvas" style="width: %(width)ipx; height: %(height)ipx; float: left;"></div>
            <div style="width: 600px; float: right;"><span style="font-size: smaller;">City, Country:</span>
                <input id="city_country" type="text" value="%(country_city)s" style="width: 120px;" />
                <span style="font-size: smaller;">Street address:</span>
                <input id="address" type="text" value="" style="width: 200px; height: 15px; margin-right: 10px;" /><br />
                <input type="button" value="Find" style="width: 60px; height: 21px;" onclick="codeAddress()" />
                <input type="button" value="Reset point" style="height: 21px;" onclick="reset_point(center)" />
                <br style="clear: both" />
                <div id="search_results"></div></div>

            """ % {'latitude': attrs['id'], 'longitude': self.attrs['longitude_id'], 'base_point' : self.attrs['base_point'],
                   'width': self.attrs['width'], 'height': self.attrs['height'], 'country_city': self.attrs['country_city']}

        rendered = super(GoogleMapsWidget, self).render(name, value, attrs)
        return rendered + mark_safe(maps_html)
