""" Service for database queries """
from datetime import datetime, timezone
from bson import ObjectId
from flask import current_app
import os

from colorimetry.extensions import bcrypt, mongo

def get_site_collection():
    return current_app.db.sites


def get_sample_collection():
    return current_app.db.samples


def get_assay_collection():
    return current_app.db.assays


def get_raw_image_details():
    return current_app.db.raw_image


def get_image_jobs_collection():
    return current_app.db.image_jobs


def retrieve_sites():
    collection = get_site_collection()
    sites = collection.find({})

    site_list = []

    for s in sites:
        name = s.get("properties",{}).get("name")
        if name:
            site_list.append(name)

    return site_list


def insert_site(site):
    current_app.db.sites.insert_one(site)


def retrieve_all_assays():
    assay_collection = get_assay_collection()
    assays = assay_collection.find({})

    assay_list = []
    for a in assays:
        assay = a.get("assay")
        if assay:
            assay_list.append(assay)

    return assay_list


def retrieve_all_site_samples(site_name):
    sites = get_site_collection()

    site = sites.find_one(
        {"properties.name": site_name},
        {"geometry": 1}
    )

    if not site:
        return []

    polygon = site["geometry"]

    samples = get_sample_collection()
    site_samples = samples.find({
        "geometry":{
            "$geoWithin": {
                "$geometry": polygon
            }
        }
    })

    return list(site_samples)



def parse_date_str(d):
    """Convert 'YYYY-MM-DD' into a datetime object at midnight."""
    if not d:
        return None
    return datetime.strptime(d, "%Y-%m-%d")


def retrieve_filtered_samples(site_name=None, start_date=None,
                              end_date=None):
    samples = get_sample_collection()
    query = {}

    if site_name:
        sites = get_site_collection()
        site = sites.find_one(
            {"properties.name": site_name},
            {"geometry": 1}
        )

        if not site:
            return []

        polygon = site["geometry"]

        query["geometry"] = {
            "$geoWithin": {"$geometry": polygon}
        }


    start_dt = parse_date_str(start_date)
    end_dt = parse_date_str(end_date)

    timestamp_filter = {}

    if start_dt and not end_dt:
        timestamp_filter["$gte"] = start_dt
        timestamp_filter["$lte"] = datetime.max

    elif end_dt and not start_dt:
        timestamp_filter["$lte"] = end_dt

    elif start_dt and end_dt:
        timestamp_filter["$gte"] = start_dt
        timestamp_filter["$lte"] = end_dt

    print(timestamp_filter)
    if timestamp_filter:
        query["properties.submission_timestamp"] = timestamp_filter

    return list(samples.find(query).sort("properties.submission_timestamp", -1))



def get_all_samples_ordered():
    samples = current_app.db.samples.find().sort("properties.submission_timestamp", -1)
    return list(samples)


def get_last_ten_samples(limit: int = 10):
    samples = current_app.db.samples.find().sort("properties.submission_timestamp", -1).limit(limit)
    return list(samples)


def get_user_samples(user:str):
    samples = (
        current_app.db.samples.find({"properties.user": user,
                                     "properties.deleted": False})
        .sort("properties.submission_timestamp", -1)
    )

    return list(samples)


def get_last_ten_user_samples(user:str, limit: int=10):
    samples = (
        current_app.db.samples.find({"properties.user": user})
        .sort("properties.submission_timestamp", -1).limit(limit)
    )

    return list(samples)


def retrieve_single_sample(sample_id:str):
    return current_app.db.samples.find_one({"_id": ObjectId(sample_id)})


def retrieve_single_image(filename:str):
    return current_app.db.raw_image.find_one({"filename": filename})


def set_deleted_flag(sample_id:str):
    return current_app.db.samples.update_one({"_id": ObjectId(sample_id)},
                                       {"$set": {"properties.deleted": True}})


def delete_single_sample(sample_id:str):
    sample = retrieve_single_sample(sample_id)
    observations = sample.get("properties", {}).get("observations", [])
    filename = observations[0].get("filename") if observations else None

    image = retrieve_single_image(filename)
    filepath = image.get("filepath")
    if filepath.endswith(filename):
        image_path = filepath
    else:
        image_path = os.path.join(filepath, filename)

    os.remove(image_path)

    return current_app.db.samples.delete_one({"_id": ObjectId(sample_id)})


def delete_site(site:str):
    return current_app.db.sites.delete_one({"properties.name": site})


def get_total_sample_count():
    return get_sample_collection().count_documents({"properties.deleted": False})


def get_deleted_sample_count():
    return get_sample_collection().count_documents({"properties.deleted": True})


def get_deleted_samples():
    samples = (current_app.db.samples.find({"properties.deleted": True})
               .sort("properties.submission_timestamp", -1))
    return samples


def paginated_sample_list(page:int, per_page:int):
    samples = (current_app.db.samples.find({"properties.deleted": False})
               .sort("properties.submission_timestamp", -1)
               .skip((page - 1) * per_page).limit(per_page))

    return list(samples)


def paginated_deleted_sample_list(page:int, per_page:int):
    samples = (current_app.db.samples.find({"properties.deleted": True})
               .sort("properties.submission_timestamp", -1)
               .skip((page - 1) * per_page).limit(per_page))

    return list(samples)


def get_assay_data(assay:str):
    return current_app.db.assays.find_one({"assay":assay})
