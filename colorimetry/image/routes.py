""" Image routes """
from datetime import datetime, timezone
import os
from bson import ObjectId
from flask import (render_template, url_for,
                   Blueprint, current_app, redirect, abort, flash)
from flask_login import login_required, current_user
from PIL import Image
from werkzeug.utils import secure_filename
from colorimetry.services.image_service import (extract_exif,
                                                circle_recognition,
                                                get_cropped_image)
from colorimetry.services.query_service import (get_sample_collection,
                                                get_raw_image_details,
                                                retrieve_all_assays,
                                                get_image_jobs_collection,
                                                get_assay_data)
from colorimetry.image.forms import (ImageDetailsForm,
                                     ImageDetailsNotesForm,
                                     ImageUploadForm)
from threading import Thread


image = Blueprint('image', __name__)
UPLOAD_FOLDER = os.path.join("static", "uploaded_images")


@image.route("/upload_image", methods=["GET", "POST"])
@login_required
def upload_image():
    form = ImageUploadForm()

    assays = retrieve_all_assays()
    form.assay.choices = [(a, a) for a in assays]

    if form.validate_on_submit():
        file = form.image.data
        assay = form.assay.data

        dt = datetime.now(timezone.utc)
        timestamp = dt.strftime("%Y%m%d%H%M%S%f")
        ext = os.path.splitext(secure_filename(file.filename))[1]
        new_filename = timestamp + ext

        filepath = os.path.join(
            current_app.root_path,
            "static",
            "uploaded_images",
            new_filename
        )

        file.save(filepath)

        jobs = get_image_jobs_collection()
        job = {
            "status": "processing",
            "result_id": None,
            "redirect_route": None,
            "error": None,
            "user_id": current_user.get_id()
        }
        job_id = jobs.insert_one(job).inserted_id

        Thread(
            target=process_image_job,
            name=f"image-job-{job_id}",
            args=(
                current_app._get_current_object(),
                str(job_id),
                filepath,
                assay,
                current_user.get_id()
            ),
            daemon=True
        ).start()

        return redirect(url_for("image.processing", job_id=str(job_id)))

    return render_template(
        "image/upload_image.html",
        title="Upload Image",
        form=form
    )



@image.route("/image_details/<raw_image_id>", methods=["GET", "POST"])
@login_required
def image_details(raw_image_id):
    form = ImageDetailsForm()
    raw_image = get_raw_image_details()
    raw_image_details = raw_image.find_one({"_id": ObjectId(raw_image_id)})
    if not raw_image_details:
        abort(404)
    if form.validate_on_submit():
        raw_image_details['latitude'] = form.latitude.data
        raw_image_details['longitude'] = form.longitude.data
        raw_image_details['notes'] = form.notes.data
        record = add_record(raw_image_details)
        samples = get_sample_collection()
        samples.insert_one(record)
        return redirect(url_for('users.account'))
    return render_template('image/image_details.html',
                           form=form, title='Image Details')


@image.route("/image_details_notes/<raw_image_id>", methods=["GET", "POST"])
@login_required
def image_details_notes(raw_image_id):
    form = ImageDetailsNotesForm()
    raw_image = get_raw_image_details()
    raw_image_details = raw_image.find_one({"_id": ObjectId(raw_image_id)})
    if not raw_image_details:
        abort(404)
    if form.validate_on_submit():
        raw_image_details['notes'] = form.notes.data
        record = add_record(raw_image_details)
        samples = get_sample_collection()
        samples.insert_one(record)
        return redirect(url_for('users.account'))
    return render_template('image/image_details_notes.html',
                           form=form, title='Image Details')


@image.route("/processing/<job_id>")
@login_required
def processing(job_id):
    return render_template("image/processing.html", job_id=job_id)


@image.route("/job_status/<job_id>")
@login_required
def job_status(job_id):
    jobs = get_image_jobs_collection()

    job = jobs.find_one({"_id": ObjectId(job_id)})

    if not job:
        return {"status": "not_found"}, 404

    return {
        "status": job["status"],
        "result_id": job.get("result_id"),
        "redirect_route": job.get("redirect_route"),
        "error": job.get("error")
    }


def process_image_job(app, job_id, filepath, assay, user_id):
    with app.app_context():
        jobs = get_image_jobs_collection()
        raw_image = get_raw_image_details()

        try:
            cropped_file = get_cropped_image(filepath)

            circle_data = circle_recognition(cropped_file, assay)
            os.remove(cropped_file)

            this_assay_values = get_assay_data(assay)

            if not circle_data.circle_found:
                raise Exception("Circle detection failed")

            new_image = Image.open(filepath)

            try:
                exif = extract_exif(new_image)
            except:
                exif = {}

            exif_datetime = exif.get("ExifDateTime") if exif else None
            lon = exif.get("Longitude") if exif and exif.get("LocationFound") else None
            lat = exif.get("Latitude") if exif and exif.get("LocationFound") else None

            circle_dict = vars(circle_data)

            raw_image_data = {
                "filename": os.path.basename(filepath),
                "filepath": filepath,
                "circle_data": circle_dict,
                "longitude": lon,
                "latitude": lat,
                "timestamp": exif_datetime,
                "user_id": user_id,
                "notes": None,
                "assay": assay
            }

            result = raw_image.insert_one(raw_image_data)

            new_image = new_image.resize(
                (int(new_image.width * 0.5), int(new_image.height * 0.5)),
                Image.Resampling.LANCZOS
            )
            new_image.save(filepath)

            redirect_route = (
                "image.image_details_notes" if lon is not None
                else "image.image_details"
            )

            jobs.update_one(
                {"_id": ObjectId(job_id)},
                {"$set": {
                    "status": "done",
                    "result_id": str(result.inserted_id),
                    "redirect_route": redirect_route
                }}
            )

        except Exception as e:
            jobs.update_one(
                {"_id": ObjectId(job_id)},
                {"$set": {
                    "status": "failed",
                    "error": str(e)
                }}
            )

            try:
                os.remove(filepath)
            except:
                pass


def add_record(raw_image_details):

    obs_list = [{
        "filename": raw_image_details['filename'],
        "image_timestamp": raw_image_details['timestamp'],
        "cup_blue": raw_image_details['circle_data']['cup_blue'],
        "cup_red": raw_image_details['circle_data']['cup_red'],
        "cup_green": raw_image_details['circle_data']['cup_green'],
        "bgd_blue": raw_image_details['circle_data']['paper_blue'],
        "bgd_red": raw_image_details['circle_data']['paper_red'],
        "bgd_green": raw_image_details['circle_data']['paper_green'],

    }]

    record = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            # GeoJSON MUST be [lon, lat]
            "coordinates": [raw_image_details['longitude'],
                            raw_image_details['latitude']],
        },
        "properties": {
            "assay": raw_image_details['assay'],
            "doc": raw_image_details['circle_data']['doc'],
            "user":  current_user.username,
            "notes": raw_image_details['notes'],
            "deleted": False,
            "submission_timestamp": datetime.now(timezone.utc),
            "observations": obs_list,
        }
    }

    return record


