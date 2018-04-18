import math
import requests
import json
import os
from bs4 import BeautifulSoup

from color_dicts import mpl_color_map, html_color_codes, ncaa_logos


def safe_iter(var):
    try:
        return iter(var)
    except TypeError:
        return [var]


class GoogleMapPlotter(object):

    def __init__(self, center_lat, center_lng, zoom):
        self.center = (float(center_lat), float(center_lng))
        self.zoom = int(zoom)
        self.grids = None
        self.paths = []
        self.shapes = []
        self.markers = []
        self.heatmap_points = []
        self.radpoints = []
        self.gridsetting = None
        self.coloricon = os.path.join(os.path.dirname(__file__), 'markers/%s.png')
        self.coloricons = []
        self.color_dict = mpl_color_map
        self.html_color_codes = html_color_codes
        self.ncaa_logos = ncaa_logos
        self.infowindows = []
        self.marker_clusterer = None

    @classmethod
    def from_geocode(cls, location_string, zoom=13):
        lat, lng = cls.geocode(location_string)
        return cls(lat, lng, zoom)

    @classmethod
    def geocode(self, location_string):
        geocode = requests.get(
            'http://maps.googleapis.com/maps/api/geocode/json?address="%s"' % location_string)
        geocode = json.loads(geocode.text)
        latlng_dict = geocode['results'][0]['geometry']['location']
        return latlng_dict['lat'], latlng_dict['lng']

    def grid(self, slat, elat, latin, slng, elng, lngin):
        self.gridsetting = [slat, elat, latin, slng, elng, lngin]

    def marker(self, lat, lng, color, title="no implementation", draggable=False):
        color = self.color_dict.get(color, color)
        color = self.html_color_codes.get(color, color)
        marker_name = "marker%s" % str(len(self.markers)+1)
        index = len(self.markers) # ADDING THIS TO INDEX THE IMAGES
        self.markers.append((marker_name, lat, lng, color, title, draggable, index))
        return marker_name

    def infowindow(self, marker_name, content, always_open=False):
        infowindow_name = "infowindow%s" % str(len(self.infowindows)+1)
        self.infowindows.append((infowindow_name, marker_name, content, always_open))
        return infowindow_name

    def markerClusterer(self, markers_names, maxZoom):
        self.marker_clusterer = (markers_names, maxZoom)

    def scatter(self, lats, lngs, color=None, size=None, marker=True, c=None, s=None, **kwargs):
        color = color or c
        size = size or s or 40
        kwargs["color"] = color
        kwargs["size"] = size
        settings = self._process_kwargs(kwargs)
        for lat, lng in zip(lats, lngs):
            if marker:
                self.marker(lat, lng, settings['color'])
            else:
                self.circle(lat, lng, size, **settings)

    def circle(self, lat, lng, radius, color=None, c=None, **kwargs):
        color = color or c
        kwargs.setdefault('face_alpha', 0.5)
        kwargs.setdefault('face_color', "#000000")
        kwargs.setdefault("color", color)
        settings = self._process_kwargs(kwargs)
        path = self.get_cycle(lat, lng, radius)
        self.shapes.append((path, settings))

    def _process_kwargs(self, kwargs):
        settings = dict()
        settings["edge_color"] = kwargs.get("color", None) or \
                                 kwargs.get("edge_color", None) or \
                                 kwargs.get("ec", None) or \
                                 "#000000"

        settings["edge_alpha"] = kwargs.get("alpha", None) or \
                                 kwargs.get("edge_alpha", None) or \
                                 kwargs.get("ea", None) or \
                                 1.0
        settings["edge_width"] = kwargs.get("edge_width", None) or \
                                 kwargs.get("ew", None) or \
                                 1.0
        settings["face_alpha"] = kwargs.get("alpha", None) or \
                                 kwargs.get("face_alpha", None) or \
                                 kwargs.get("fa", None) or \
                                 0.3
        settings["face_color"] = kwargs.get("color", None) or \
                                 kwargs.get("face_color", None) or \
                                 kwargs.get("fc", None) or \
                                 "#000000"

        settings["color"] = kwargs.get("color", None) or \
                            kwargs.get("c", None) or \
                            settings["edge_color"] or \
                            settings["face_color"]

        # Need to replace "plum" with "#DDA0DD" and "c" with "#00FFFF" (cyan).
        for key, color in settings.items():
            if 'color' in key:
                color = self.color_dict.get(color, color)
                color = self.html_color_codes.get(color, color)
                settings[key] = color

        settings["closed"] = kwargs.get("closed", None)

        return settings

    def plot(self, lats, lngs, color=None, c=None, **kwargs):
        color = color or c
        kwargs.setdefault("color", color)
        settings = self._process_kwargs(kwargs)
        path = zip(lats, lngs)
        self.paths.append((path, settings))

    def heatmap(self, lats, lngs, threshold=10, radius=10, gradient=None, opacity=0.6, dissipating=True):
        """
        :param lats: list of latitudes
        :param lngs: list of longitudes
        :param threshold:
        :param radius: The hardest param. Example (string):
        :return:
        """
        settings = {}
        settings['threshold'] = threshold
        settings['radius'] = radius
        settings['gradient'] = gradient
        settings['opacity'] = opacity
        settings['dissipating'] = dissipating
        settings = self._process_heatmap_kwargs(settings)

        heatmap_points = []
        for lat, lng in zip(lats, lngs):
            heatmap_points.append((lat, lng))
        self.heatmap_points.append((heatmap_points, settings))

    def _process_heatmap_kwargs(self, settings_dict):
        settings_string = ''
        settings_string += "heatmap.set('threshold', %d);\n" % settings_dict['threshold']
        settings_string += "heatmap.set('radius', %d);\n" % settings_dict['radius']
        settings_string += "heatmap.set('opacity', %f);\n" % settings_dict['opacity']

        dissipation_string = 'true' if settings_dict['dissipating'] else 'false'
        settings_string += "heatmap.set('dissipating', %s);\n" % (dissipation_string)

        gradient = settings_dict['gradient']
        if gradient:
            gradient_string = "var gradient = [\n"
            for r, g, b, a in gradient:
                gradient_string += "\t" + "'rgba(%d, %d, %d, %d)',\n" % (r, g, b, a)
            gradient_string += '];' + '\n'
            gradient_string += "heatmap.set('gradient', gradient);\n"

            settings_string += gradient_string

        return settings_string

    def polygon(self, lats, lngs, color=None, c=None, **kwargs):
        color = color or c
        kwargs.setdefault("color", color)
        settings = self._process_kwargs(kwargs)
        shape = zip(lats, lngs)
        self.shapes.append((shape, settings))

    # create the html file which include one google map and all points and
    # paths
    def draw(self, htmlfile):
        f = open(htmlfile, 'w')
        f.write('<html>\n')
        f.write('<head>\n')
        f.write(
            '<meta name="viewport" content="initial-scale=1.0, user-scalable=no" />\n')
        f.write(
            '<meta http-equiv="content-type" content="text/html; charset=UTF-8"/>\n')
        f.write('<title>Google Maps - pygmaps </title>\n')
        f.write('<script type="text/javascript" src="https://maps.googleapis.com/maps/api/js?libraries=visualization&sensor=true_or_false"></script>\n')
        f.write('<script type="text/javascript">\n')
        f.write('\tfunction initialize() {\n')
        self.write_map(f)
        self.write_grids(f)
        self.write_markers(f)
        self.write_infowindows(f)
        self.write_markerclusterer(f)
        self.write_paths(f)
        self.write_shapes(f)
        self.write_heatmap(f)
        f.write('\t}\n')
        f.write('</script>\n')
        self.write_markerclusterer_dependencies(f)
        f.write('</head>\n')
        f.write(
            '<body style="margin:0px; padding:0px;" onload="initialize()">\n')
        f.write(
            '\t<div id="map_canvas" style="width: 100%; height: 100%;"></div>\n')
        f.write('</body>\n')
        f.write('</html>\n')
        f.close()

    #############################################
    # # # # # # Low level Map Drawing # # # # # #
    #############################################

    def write_grids(self, f):
        if self.gridsetting is None:
            return
        slat = self.gridsetting[0]
        elat = self.gridsetting[1]
        latin = self.gridsetting[2]
        slng = self.gridsetting[3]
        elng = self.gridsetting[4]
        lngin = self.gridsetting[5]
        self.grids = []

        r = [
            slat + float(x) * latin for x in range(0, int((elat - slat) / latin))]
        for lat in r:
            self.grids.append(
                [(lat + latin / 2.0, slng + lngin / 2.0), (lat + latin / 2.0, elng + lngin / 2.0)])

        r = [
            slng + float(x) * lngin for x in range(0, int((elng - slng) / lngin))]
        for lng in r:
            self.grids.append(
                [(slat + latin / 2.0, lng + lngin / 2.0), (elat + latin / 2.0, lng + lngin / 2.0)])

        for line in self.grids:
            settings = self._process_kwargs({"color": "#000000"})
            self.write_polyline(f, line, settings)

    def write_markers(self, f):
        for marker in self.markers:
            self.write_marker(f, marker[0], marker[1], marker[2], marker[3], marker[4], marker[5], marker[6])

    def write_infowindows(self, f):
        for infowindow in self.infowindows:
            self.write_infowindow(f, infowindow[0], infowindow[1], infowindow[2], infowindow[3])

    def get_cycle(self, lat, lng, rad):
        # unit of radius: meter
        cycle = []
        d = (rad / 1000.0) / 6378.8
        lat1 = (math.pi / 180.0) * lat
        lng1 = (math.pi / 180.0) * lng

        r = [x * 10 for x in range(36)]
        for a in r:
            tc = (math.pi / 180.0) * a
            y = math.asin(
                math.sin(lat1) * math.cos(d) + math.cos(lat1) * math.sin(d) * math.cos(tc))
            dlng = math.atan2(math.sin(
                tc) * math.sin(d) * math.cos(lat1), math.cos(d) - math.sin(lat1) * math.sin(y))
            x = ((lng1 - dlng + math.pi) % (2.0 * math.pi)) - math.pi
            cycle.append(
                (float(y * (180.0 / math.pi)), float(x * (180.0 / math.pi))))
        return cycle

    def write_paths(self, f):
        for path, settings in self.paths:
            self.write_polyline(f, path, settings)

    def write_shapes(self, f):
        for shape, settings in self.shapes:
            self.write_polygon(f, shape, settings)

    # TODO: Add support for mapTypeId: google.maps.MapTypeId.SATELLITE
    def write_map(self,  f):
        f.write('\t\tvar centerlatlng = new google.maps.LatLng(%f, %f);\n' %
                (self.center[0], self.center[1]))
        f.write('\t\tvar myOptions = {\n')
        f.write('\t\t\tzoom: %d,\n' % (self.zoom))
        f.write('\t\t\tcenter: centerlatlng,\n')
        #f.write('\t\t\tmapTypeId: google.maps.MapTypeId.SATELLITE\n')
        #f.write('\t\t\tmapTypeId: google.maps.MapTypeId.ROADMAP\n')
        f.write('\t\t\tmapTypeId: google.maps.MapTypeId.HYBRID\n')

        f.write('\t\t};\n')
        f.write(
            '\t\tvar map = new google.maps.Map(document.getElementById("map_canvas"), myOptions);\n')
        f.write('\n')

    def write_marker(self, f, marker_name, lat, lon, color, title, draggable, index):
        f.write('\t\tvar latlng = new google.maps.LatLng(%f, %f);\n' %
                (lat, lon))
        f.write('\t\tvar img = new google.maps.MarkerImage(\'%s\');\n' %
                (self.coloricons[index])) # RIGHT HERE!!!!
        f.write('\t\tvar %s = new google.maps.Marker({\n' % marker_name)
        f.write('\t\t\ttitle: "%s",\n' % title)
        f.write('\t\t\ticon: img,\n')
        f.write('\t\t\tposition: latlng,\n')
        f.write('\t\t\tdraggable: %s\n' % str(draggable).lower())
        f.write('\t\t});\n')
        f.write('\t\t%s.setMap(map);\n' % marker_name)
        f.write('\n')

    def write_infowindow(self, f, infowindow_name, marker_name, content, always_open):
        f.write('\t\tvar %s = new google.maps.InfoWindow({\n' % infowindow_name)
        f.write('\t\t\tcontent: "%s"\n' % content)
        f.write('\t\t});\n')
        f.write('\t\tgoogle.maps.event.addListener(%s, "click", function(e) {\n' % marker_name)
        f.write('\t\t\t%s.open(map, this);\n' % infowindow_name)
        f.write('\t\t});\n')
        if (always_open):
            f.write('\t\t%s.open(map, %s);\n' % (infowindow_name, marker_name))
        f.write('\n')
        
    def write_markerclusterer(self, f):
        if self.marker_clusterer:
            markers_names = '['+', '.join(self.marker_clusterer[0])+']'
            f.write('\t\tvar markerCluster = new MarkerClusterer(map, %s,\n' % markers_names);
            f.write('\t\t\t{imagePath: "https://developers.google.com/maps/documentation/javascript/examples/markerclusterer/m", maxZoom: %s});\n\n' % self.marker_clusterer[1]);

    def write_markerclusterer_dependencies(self, f):
        if self.marker_clusterer:
            f.write('<script src="https://developers.google.com/maps/documentation/javascript/examples/markerclusterer/markerclusterer.js"></script>\n')

    def write_polyline(self, f, path, settings):
        clickable = False
        geodesic = True
        strokeColor = settings.get('color') or settings.get('edge_color')
        strokeOpacity = settings.get('edge_alpha')
        strokeWeight = settings.get('edge_width')

        f.write('\t\tvar PolylineCoordinates = [\n')
        for coordinate in path:
            f.write('\t\t\tnew google.maps.LatLng(%f, %f),\n' %
                    (coordinate[0], coordinate[1]))
        f.write('\t\t];\n')
        f.write('\n')

        f.write('\t\tvar Path = new google.maps.Polyline({\n')
        f.write('\t\t\tclickable: %s,\n' % (str(clickable).lower()))
        f.write('\t\t\tgeodesic: %s,\n' % (str(geodesic).lower()))
        f.write('\t\t\tpath: PolylineCoordinates,\n')
        f.write('\t\t\tstrokeColor: "%s",\n' % (strokeColor))
        f.write('\t\t\tstrokeOpacity: %f,\n' % (strokeOpacity))
        f.write('\t\t\tstrokeWeight: %d\n' % (strokeWeight))
        f.write('\t\t});\n')
        f.write('\n')
        f.write('\t\tPath.setMap(map);\n')
        f.write('\n\n')

    def write_polygon(self, f, path, settings):
        clickable = False
        geodesic = True
        strokeColor = settings.get('edge_color') or settings.get('color')
        strokeOpacity = settings.get('edge_alpha')
        strokeWeight = settings.get('edge_width')
        fillColor = settings.get('face_color') or settings.get('color')
        fillOpacity= settings.get('face_alpha')
        f.write('var coords = [\n')
        for coordinate in path:
            f.write('new google.maps.LatLng(%f, %f),\n' %
                    (coordinate[0], coordinate[1]))
        f.write('];\n')
        f.write('\n')

        f.write('var polygon = new google.maps.Polygon({\n')
        f.write('clickable: %s,\n' % (str(clickable).lower()))
        f.write('geodesic: %s,\n' % (str(geodesic).lower()))
        f.write('fillColor: "%s",\n' % (fillColor))
        f.write('fillOpacity: %f,\n' % (fillOpacity))
        f.write('paths: coords,\n')
        f.write('strokeColor: "%s",\n' % (strokeColor))
        f.write('strokeOpacity: %f,\n' % (strokeOpacity))
        f.write('strokeWeight: %d\n' % (strokeWeight))
        f.write('});\n')
        f.write('\n')
        f.write('polygon.setMap(map);\n')
        f.write('\n\n')

    def write_heatmap(self, f):
        for heatmap_points, settings_string in self.heatmap_points:
            f.write('var heatmap_points = [\n')
            for heatmap_lat, heatmap_lng in heatmap_points:
                f.write('new google.maps.LatLng(%f, %f),\n' %
                        (heatmap_lat, heatmap_lng))
            f.write('];\n')
            f.write('\n')
            f.write('var pointArray = new google.maps.MVCArray(heatmap_points);' + '\n')
            f.write('var heatmap;' + '\n')
            f.write('heatmap = new google.maps.visualization.HeatmapLayer({' + '\n')
            f.write('\n')
            f.write('data: pointArray' + '\n')
            f.write('});' + '\n')
            f.write('heatmap.setMap(map);' + '\n')
            f.write(settings_string)

def insertapikey(page_name, apikey):
    """put the google api key in a html file"""
    def putkey(page, apikey, apistring=None):
        """put the apikey in the htmltxt and return soup"""
        if not apistring:
            apistring = "https://maps.googleapis.com/maps/api/js?key=%s&libraries=visualization&sensor=true_or_false&callback=initialize"
        soup = BeautifulSoup(page, 'html.parser')
        body = soup.body
        src = apistring % (apikey) # insert apikey for %s
        insert_tag = soup.new_tag("script", src=src, async="defer")
        body.insert(-1, insert_tag) # put the new script in with new src
        return soup
    page = open(page_name, 'r').read()
    soup = putkey(page, apikey)
    new_page_text = soup.prettify() # format it
    open(page_name, 'w').write(new_page_text) # rewrite the page

if __name__ == "__main__":
    mymap = GoogleMapPlotter(39.8097343, -98.5556, 5)
    #mymap = GoogleMapPlotter.from_geocode("Stanford University")

    #mymap.grid(37.42, 37.43, 0.001, -122.15, -122.14, 0.001)
    #mymap.marker(37.427, -122.145, "yellow")
    #mymap.marker(37.428, -122.146, "cornflowerblue")
    #mymap.marker(37.429, -122.144, "k")

    mymap.coloricons.append("http://i.turner.ncaa.com/dr/ncaa/ncaa7/release/sites/default/files/images/logos/schools/a/arizona-st.40.png")
    mymap.coloricons.append("http://i.turner.ncaa.com/dr/ncaa/ncaa7/release/sites/default/files/images/logos/schools/m/michigan.40.png")
    marker = mymap.marker(33.45343, -112.073231, "red")
    marker2 = mymap.marker(42.276061, -83.743121, "red")


    mymap.infowindow(marker, "Arizona State University</br><a href=http://www.asu.edu/>www.asu.edu</a>", False)
    mymap.infowindow(marker2, "<h3>University of Michigan</h3>Ann Arbor, MI</br>Enrollment: 44,642</br> <a href=http://www.umich.edu>www.umich.edu</a></br><h3>Parker Class of 2007-2017:</br>42 students attended</h3>", False)

    #mymap.map_type = 'google.maps.MapTypeId.HYBRID'
    #mymap.circle(37.429, -122.145, 100, "#FF0000", ew=2)
    #path = [(37.429, 37.428, 37.427, 37.427, 37.427),
             #(-122.145, -122.145, -122.145, -122.146, -122.146)]
    #path2 = [[i+.01 for i in path[0]], [i+.02 for i in path[1]]]
    #path3 = [(37.433302 , 37.431257 , 37.427644 , 37.430303), (-122.14488, -122.133121, -122.137799, -122.148743)]
    #path4 = [(37.423074, 37.422700, 37.422410, 37.422188, 37.422274, 37.422495, 37.422962, 37.423552, 37.424387, 37.425920, 37.425937),
         #(-122.150288, -122.149794, -122.148936, -122.148142, -122.146747, -122.14561, -122.144773, -122.143936, -122.142992, -122.147863, -122.145953)]
    #mymap.plot(path[0], path[1], "plum", edge_width=10)
    ##mymap.plot(path2[0], path2[1], "red")
    #mymap.polygon(path3[0], path3[1], edge_color="cyan", edge_width=5, face_color="blue", face_alpha=0.1)
    #mymap.heatmap(path4[0], path4[1], threshold=10, radius=40)
    #mymap.heatmap(path3[0], path3[1], threshold=10, radius=40, dissipating=False, gradient=[(30,30,30,0), (30,30,30,1), (50, 50, 50, 1)])
    #mymap.scatter(path4[0], path4[1], c='r', marker=True)
    #mymap.scatter(path4[0], path4[1], s=90, marker=False, alpha=0.1)
    # Get more points with:
    # http://www.findlatitudeandlongitude.com/click-lat-lng-list/
    #scatter_path = ([37.424435, 37.424417, 37.424417, 37.424554, 37.424775, 37.425099, 37.425235, 37.425082, 37.424656, 37.423957, 37.422952, 37.421759, 37.420447, 37.419135, 37.417822, 37.417209],
                    #[-122.142048, -122.141275, -122.140503, -122.139688, -122.138872, -122.138078, -122.137241, -122.136405, -122.135568, -122.134731, -122.133894, -122.133057, -122.13222, -122.131383, -122.130557, -122.129999])
    #mymap.scatter(scatter_path[0], scatter_path[1], c='r', marker=True)
    mymap.draw('mymap.html')
    insertapikey('mymap.html',"AIzaSyD65be4pywe7-y4GjMmzZMidOpdmu2lkXo")
