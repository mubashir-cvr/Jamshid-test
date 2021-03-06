import json

from django.contrib.gis.geos import GEOSGeometry, Polygon
from django.core.serializers import serialize
from django.conf import settings
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.db.models import F
from .models import Camp, Hazard, Person
from .forms import RescueForm, HazardForm, PersonForm, MissingPersonForm

def camps_geojson(request):
    """
    Retrieves properties given the querystring params, and 
    returns them as GeoJSON.
    """
    ne = request.GET["ne"].split(",")
    sw = request.GET["sw"].split(",")
    lookup = {
        "point__contained": Polygon.from_bbox((sw[1], sw[0], ne[1], ne[0])),
    }
    properties = Camp.objects.filter(**lookup)
    json = serialize("geojson", properties, geometry_field="point")

    return HttpResponse(json, content_type="application/json")

def hazards_geojson(request):
    """
    Retrieves properties given the querystring params, and 
    returns them as GeoJSON.
    """
    ne = request.GET["ne"].split(",")
    sw = request.GET["sw"].split(",")
    lookup = {
        "point__contained": Polygon.from_bbox((sw[1], sw[0], ne[1], ne[0])),
    }
    properties = Hazard.objects.filter(**lookup)
    json = serialize("geojson", properties, geometry_field="point")

    return HttpResponse(json, content_type="application/json")

def people_geojson(request):
    """
    Retrieves properties given the querystring params, and 
    returns them as GeoJSON.
    """
    ne = request.GET["ne"].split(",")
    sw = request.GET["sw"].split(",")
    lookup = {
        "point__contained": Polygon.from_bbox((sw[1], sw[0], ne[1], ne[0])),
    }
    people = Person.objects.filter(**lookup)
    json = serialize("geojson", people, geometry_field="point")

    return HttpResponse(json, content_type="application/json")

@csrf_exempt
def add_hazard_area(request):
    # Get the post variables
    response = json.loads(request.body)
    form = HazardForm(response['data'])
    if form.is_valid():
        latlng = response['latlng']
        point = GEOSGeometry("POINT(%(lng)s %(lat)s)" % latlng)
        if (Hazard.objects.filter(point = point).count() == 0):
            try:
                hazard = Hazard.objects.create(description = response['data']['description'])
                hazard.set_hazard_location(latlng = latlng)
                hazard.save()
                response = {
                    'status': 200,
                    'message': 'Saved hazard location @' + str(latlng),
                }
            except Exception as e:
                response = {
                    'status': 404,
                    'message': 'Something went wrong: ' + str(e) 
                }
        else:
            hazard = Hazard.objects.filter(point = point).update(vote=F('weight') + 1)
            response = {
                'status': 404,
                'message': 'Weight updated.'
            }
    else:
        response = {
            'status': 404,
            'message': 'Invalid form, re-enter.'
        }
    return HttpResponse(json.dumps(response), content_type="application/json")

@csrf_exempt
def add_rescue_area(request):
    response = json.loads(request.body)
    form = RescueForm(response['data'])
    if form.is_valid():
        latlng = response['latlng']
        try:
            person = Person.objects.create(name = response['data']['name'],
                                        phone = response['data']['phone'],
                                        emergencyName = response['data']['emergencyName'],
                                        emergencyPhone = response['data']['emergencyPhone']
                                        )
            person.set_location(latlng = latlng)
            person.save()
            response = {
                'status': 200,
                'message': 'Your location saved @' + str(latlng)
            }
        except Exception as e:
            response = {
                'status': 404,
                'message': 'Something went wrong: ' + str(e) 
            }
    else:
        response = {
            'status': 404,
            'message': 'Invalid form, re-enter.'
        }
    return HttpResponse(json.dumps(response), content_type="application/json")

def camps_map(request):
    """
    Index page for the app, with map + form for filtering 
    properties.
    """
    # Get the center of all properties, for centering the map.
    if False:
    # if Camp.objects.exists():
        cursor = connection.cursor()
        cursor.execute("SELECT ST_AsText(st_centroid(st_union(point))) FROM dashboard_camp")
        print(cursor)
        center = dict(zip(("lng", "lat"), GEOSGeometry(cursor.fetchone()[0]).get_coords()))
    else:
        # Default, when no properties exist.
        center = {"lat":37.782551, "lng": -122.445368}
        # center = {"lat": -33.864869, "lng": 151.1959212}

    context = {
        "center": json.dumps(center),
        "title": "Vigilant Exodus",
        "api_key": 'AIzaSyDnZM2wkGhX5O2CBKveClAikks8NI-WvPc',
        "distance_range": (1, 21),
    }

    return render(request, "map.html", context)

def checkin(request):
    person_form=PersonForm()
    if request.method == 'POST':
        person_form = PersonForm(request.POST)
        if person_form.is_valid():
            data = person_form.cleaned_data
            # name= data['name']
            phone = data['phone']
            person = Person.objects.filter(phone=phone).count()
            print(person)
            if person == 0:
                person_form.save(commit=True)
            else :
                person_info = Person.objects.get(phone=phone)

                return render(request,'infopage.html',{'person_info':person_info,'bool':"true"})
            person_info = "None"
            return render(request, 'infopage.html', {'person_info': person_info, 'bool': "checkinonly"})

        else :
            return HttpResponse("Form invalid")
    else :
        return render(request,'checkin.html',{'person_form':person_form})

def findmissingperson(request):
    person_form=MissingPersonForm()
    if request.method=="POST":
        person_form=MissingPersonForm(request.POST)

        if person_form.is_valid():
            data = person_form.cleaned_data
            phone = data['phone']
            person = Person.objects.filter(phone=phone).count()
            print("abcd",person)
            if person == 0:
                person_form.save(commit=True)
                person_info = "None"
                return render(request,'infopage.html',{'person_info':person_info,'bool':"missingperson"})
            else :
                person_info = Person.objects.get(phone=phone)
                return render(request,'infopage.html',{'person_info':person_info,'bool':"false"})
        else:
            return HttpResponse("invalid form")
    else:
        return render(request,'missing.html',{'person_form':person_form})

# def cluster(request):
#     query = """WITH clusters AS (
#   SELECT
#     point,
#     ST_ClusterDBSCAN(point, eps := (30 / 11111.0), minpoints := 0) OVER() AS cluster_id
#   FROM dashboard_person
#   WHERE point IS NOT NULL
# )
# SELECT
#   cluster.id,
#   ST_AsText(ST_Centroid(cluster.geometry)) AS coordinate,
#   ST_AsGeoJSON(cluster.geometry) AS geometry
# FROM (
#   SELECT
#     cluster_id AS id,
#     ST_ConvexHull(ST_Collect(point)) AS geometry
#   FROM clusters
#   GROUP BY cluster_id
# ) AS cluster;
# """
#     cursor = connection.cursor()
#     cursor.execute(query)
#     print(cursor.fetchall())
#     # print(cursor.fetchone())
#     # print(GEOSGeometry(cursor.fetchall()[0][2]).get_coords())
#     center = dict(zip(("lng", "lat"), GEOSGeometry(cursor.fetchall()[0][1]).coords))
#     return HttpResponse(json.dumps(center), content_type="application/json")