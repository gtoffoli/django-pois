// https://developers.google.com/maps/documentation/javascript/reference#Geocoder
// geocode(request:GeocoderRequest, callback:function(Array.<GeocoderResult>, GeocoderStatus))
// http://tech.cibul.net/geocode-with-google-maps-api-v3

function gmap_geocode(form) {
	el = document.getElementById('id_pro_com');
	comune = el.options[el.selectedIndex].innerHTML;
	street_address = document.getElementById('id_street_address').value;
	if (street_address) {
		address = street_address + ', ' + comune;
	} else {
		housenumber = form.elements['housenumber'].value;
		outer_span = document.getElementById('id_street-deck');
		inner_span = outer_span.children[0];
		if (typeof inner_span === "undefined")
			street_name = '';
		else
			street_name = ', ' + inner_span.textContent.trim();
		address = housenumber + street_name + ', ' + comune;
	}
	// window.alert(address);
	request = {
		address: address,
		region: 'IT'
	}
	geocoder = new google.maps.Geocoder();
	geocoder.geocode(
		request,
		function (results, status) {
			var n = results.length;
			var status = JSON.stringify(status);
			// window.alert(status + ' : ' + n);
			for (var i=0; i < n; i++) {
				var location = results[0].geometry.location;
				var latitude = location.lat().toString().slice(0,8);
				var longitude = location.lng().toString().slice(0,8);
				form.elements['latitude'].value = latitude;
				form.elements['longitude'].value = longitude;
				// window.alert(latitude + ', ' + longitude);
				break;
			}
		});
}
