var map;
var allInfos = [];
function initMap() {
  map = new google.maps.Map(document.getElementById('map'), {
    center: {lat: 37.773561, lng: -122.444323},
    zoom: 13
  });
  
  $.get('/listings.json', function(data) {
    var image = 'static/images/mlmlogo.jpg';
    for (var key in data) {
        var location = data[key];
            // Define content of infoWindow per marker
            var contentString = (
              "<div id='content'>"+
              "<h3><a href='/listings/" + location['food_id']+"'>"+location['title'] + "</a></h3>" +
              "<p>Posting user: <a href='/user/" + location['posting_user_id'] + "'>"+location['posting_user'] + "</a></p>" +
              '<p>Date Posted: ' + location['date_posted'] + '</p>'+
              '</div>'
            );

            // Create info window 
            var infoWindow = new google.maps.InfoWindow({
              content: contentString
            });
            //Keep track of all the infoWindows.
            allInfos.push(infoWindow)

            // Create marker per location object
            marker = new google.maps.Marker({
              position: {lat: location['latitude'], lng: location['longitude']},
              map: map,
              animation: google.maps.Animation.DROP,
              title: location['title'],
            });

            // Add event listeners per marker
            bindinfoWindow(marker, map, infoWindow, contentString);

    }  // END for loop
  });//end $get
}

function bindinfoWindow(marker, map, infoWindow, html) {
  google.maps.event.addListener(marker, 'click', function() {
    // Set infoWindow content and open it when user clicks.
    closeInfos();
    infoWindow.setContent(html);
    infoWindow.open(map, marker);
  });
}

function closeInfos() {
        for (i = 0; i < allInfos.length; i++) {
            allInfos[i].close();
        }
}