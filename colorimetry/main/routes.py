""" Routes for main pages """
from flask import render_template, url_for, Blueprint, request
from flask_login import current_user
from math import ceil
from colorimetry.services.query_service import (get_last_ten_samples,
                                                get_last_ten_user_samples,
                                                get_all_samples_ordered,
                                                get_total_sample_count,
                                                paginated_sample_list)

main = Blueprint('main', __name__)

def serialize_doc(doc):
    doc["_id"] = str(doc["_id"])
    return doc


@main.route("/")
@main.route("/home")
def home():
    try:
        page = max(int(request.args.get("page", 1)), 1)
    except ValueError:
        page = 1
    per_page = 10

    sample_count = get_total_sample_count()
    total_pages = max(ceil(sample_count / per_page), 1)

    if page > total_pages:
        page = total_pages

    samples = paginated_sample_list(page, per_page)

    map_samples = get_all_samples_ordered()

    for s in map_samples:
        s["properties"]["link"] = url_for(
            "data.sample",
            sample_id=s["_id"]
        )

    map_samples = [serialize_doc(s) for s in map_samples]

    return render_template('main/home.html',
                           title='Cup of Carbon - Home', samples=samples,
                           map_samples=map_samples,
                           page=page,
                           per_page=per_page,
                           sample_count=sample_count,
                           total_pages=total_pages
                           )


@main.route("/instructions")
def instructions():
    return render_template('main/instructions.html',
                           title='Instructions')
