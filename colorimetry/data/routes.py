""" Data routes """
import csv
from datetime import datetime, timezone
import io
from math import ceil
from flask import render_template, url_for, request, Blueprint, redirect, Response
from flask_login import current_user, login_required
from colorimetry.services.query_service import (retrieve_sites,
                                                retrieve_single_sample, delete_single_sample,
                                                paginated_sample_list, get_total_sample_count,
                                                get_all_samples_ordered, retrieve_filtered_samples,
                                                insert_site, set_deleted_flag, get_user_samples,
                                                delete_site)



data = Blueprint('data', __name__)

SAMPLE_CSV_HEADER = ["Longitude", "Latitude", "Assay", "DOC", "User", "Notes",
                     "Submission Date", "Date Taken", "Cup Blue", "Cup Green",
                     "Cup Red", "Bg Blue", "Bg Green", "Bg Red", "Filename"]


def serialize_doc(doc):
    doc["_id"] = str(doc["_id"])
    return doc


@data.route("/search")
def search():
    sites = retrieve_sites()
    return render_template('data/search.html',
                           title='Search', sites=sites)


@data.route("/results", methods=['GET','POST'])
def results():
    site = request.values.get("site")
    date_from = request.values.get("date_from")
    date_to = request.values.get("date_to")

    try:
        page = max(int(request.args.get("page", 1)), 1)
    except ValueError:
        page = 1
    per_page = 10

    samples=retrieve_filtered_samples(site, date_from, date_to)
    sample_count = len(samples)
    total_pages = max(ceil(sample_count / per_page), 1)

    start = (page - 1) * per_page
    end = start + per_page
    samples = samples[start:end]

    map_samples = retrieve_filtered_samples(site, date_from, date_to)

    for s in map_samples:
        s["properties"]["link"] = url_for(
            "data.sample",
            sample_id=s["_id"]
        )

    map_samples = [serialize_doc(s) for s in map_samples]

    return render_template('data/results.html',
                           title='Search Results',
                           samples=samples,
                           map_samples=map_samples,
                           page=page,
                           per_page=per_page,
                           sample_count=sample_count,
                           total_pages=total_pages,
                           site=site,
                           date_from=date_from,
                           date_to=date_to)


@data.route("/sample/<sample_id>")
def sample(sample_id):
    sample_record = retrieve_single_sample(sample_id)
    return render_template('data/sample.html',
                           title='Sample details', sample=sample_record)


@data.route("/delete/<string:sample_id>", methods=["GET"])
@login_required
def delete(sample_id):
    set_deleted_flag(sample_id)
    return redirect(url_for("users.account"))


@data.route("/remove/<string:sample_id>", methods=["GET"])
@login_required
def remove(sample_id):
    delete_single_sample(sample_id)
    return redirect(url_for("users.admin"))


@data.route("/remove_site", methods=["GET"])
@login_required
def remove_site():
    site = request.values.get("dropdown")
    print(site)
    delete_site(site)
    return redirect(url_for("users.admin"))


@data.route("/batch")
def batch():
    try:
        page = max(int(request.args.get("page", 1)), 1)
    except ValueError:
        page = 1
    per_page = 10

    sample_count = get_total_sample_count()
    total_pages = max(ceil(sample_count/per_page), 1)

    if page > total_pages:
        page = total_pages

    samples = paginated_sample_list(page, per_page)

    return render_template("data/batch.html",
                           title='Batch Sample View',
                           samples=samples,
                           page=page,
                           per_page=per_page,
                           sample_count=sample_count,
                           total_pages=total_pages)


@data.route("/batch/download")
def batch_download():
    samples = get_all_samples_ordered()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(SAMPLE_CSV_HEADER)

    for s in samples:
        properties = s.get("properties", {})
        observations = properties.get("observations")
        first = observations[0] if observations else {}

        coords = (s.get("geometry")).get("coordinates")
        longitude = coords[0]
        latitude = coords[1]

        writer.writerow([
            longitude,
            latitude,
            properties.get("assay", ""),
            properties.get("doc", ""),
            properties.get("user", ""),
            properties.get("notes", ""),
            properties.get("submission_timestamp", ""),
            first.get("image_timestamp", ""),
            first.get("cup_blue", ""),
            first.get("cup_green", ""),
            first.get("cup_red", ""),
            first.get("bgd_blue", ""),
            first.get("bgd_green", ""),
            first.get("bgd_red", ""),
            first.get("filename", "")
        ])

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    filename = f'batch_samples_{date}.csv'

    response = Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
    return response


@data.route("/filtered/download")
def filtered_download():
    site = request.values.get("site")
    date_from = request.values.get("date_from")
    date_to = request.values.get("date_to")
    print(site)

    samples = retrieve_filtered_samples(site, date_from, date_to)
    print(len(samples))

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(SAMPLE_CSV_HEADER)

    for s in samples:
        properties = s.get("properties", {})
        observations = properties.get("observations")
        first = observations[0] if observations else {}

        coords = (s.get("geometry")).get("coordinates")
        longitude = coords[0]
        latitude = coords[1]

        writer.writerow([
            longitude,
            latitude,
            properties.get("assay", ""),
            properties.get("doc", ""),
            properties.get("user", ""),
            properties.get("notes", ""),
            properties.get("submission_timestamp", ""),
            first.get("image_timestamp", ""),
            first.get("cup_blue", ""),
            first.get("cup_green", ""),
            first.get("cup_red", ""),
            first.get("bgd_blue", ""),
            first.get("bgd_green", ""),
            first.get("bgd_red", ""),
            first.get("filename", "")
        ])

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    filename = f'filtered_samples_{date}.csv'

    response = Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
    return response


@data.route("/user/download")
def user_download():
    samples = get_user_samples(current_user.username)
    print(len(samples))

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(SAMPLE_CSV_HEADER)

    for s in samples:
        properties = s.get("properties", {})
        observations = properties.get("observations")
        first = observations[0] if observations else {}

        coords = (s.get("geometry")).get("coordinates")
        longitude = coords[0]
        latitude = coords[1]

        writer.writerow([
            longitude,
            latitude,
            properties.get("assay", ""),
            properties.get("doc", ""),
            properties.get("user", ""),
            properties.get("notes", ""),
            properties.get("submission_timestamp", ""),
            first.get("image_timestamp", ""),
            first.get("cup_blue", ""),
            first.get("cup_green", ""),
            first.get("cup_red", ""),
            first.get("bgd_blue", ""),
            first.get("bgd_green", ""),
            first.get("bgd_red", ""),
            first.get("filename", "")
        ])

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    filename = f'filtered_samples_{date}.csv'

    response = Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
    return response


@login_required
@data.route('/site_form', methods=['GET'])
def site_form():
    """
    Return and add site map and form
    """
    return render_template('data/addsite.html',
                           title='Add new site')


@login_required
@data.route('/add_site', methods=['POST'])
def add_site():
    """
    Processes the site form and creates a new site representation
    as a dictionary, inserts the new record and returns the
    map page with all bothies and sites.
    N.B. Form validation is non existent. Consider wtf forms.
    """
    result = request.form
    longitude = result["Longitude"]
    latitude = result["Latitude"]
    name = result["Name"]
    polygon = [build_polygon(longitude,latitude)]
    site = {
        "type": "Feature",
        "geometry": { "type": "Polygon", "coordinates": polygon },
        "properties": { "name": name}
    }

    insert_site(site)

    return redirect(url_for("main.home"))


def build_polygon(longitude,latitude):
    """
    Takes a string of longitudes and latitudes specied by the user and convert
    to polygon specification
    :param longitude: a csv string of longitudes for all points specified
    that will have a trailing comma and may or may not have the same point
    at the start and end (i.e., polygon may not be closed off)
    :param latitude: a csv string of latitudes for all points specified
    that will have a trailing comma and may or may not have the same point
    at the start and end (i.e., polygon may not be closed off)
    :return: an array of point arrays defining the polygon
    :rtype: Array
    """
    # strip trailing comma and split into array of coordinate strings
    longitude_split = longitude.rstrip(",").split(",")
    latitude_split = latitude.rstrip(",").split(",")
    # if end point != start point, start point is duplicated to ensure a valid polygon.
    if(longitude_split[0] != longitude_split[-1] and latitude_split[0] != latitude_split[-1]):
        longitude_split.append(longitude_split[0])
        latitude_split.append(latitude_split[0])
    polygon_coords = []
    # convert to floats and build a point and add it to the polygon coords array
    for i,lng in enumerate(longitude_split):
        lng_as_float = float(lng)
        lat_as_float = float(latitude_split[i])
        polygon_coords.append([lng_as_float,lat_as_float])
    return polygon_coords
