from pathlib import Path
from pymongo import MongoClient
from bson import ObjectId

def uploaded_images_folder():
    upload_dir = Path("colorimetry/static/uploaded_images")
    upload_dir.mkdir(parents=True, exist_ok=True)

def create_assay():
    client = MongoClient("mongodb://localhost:27017/") # update connection string if needed
    db = client["colorimetry_db"]
    collection = db["assays"]
    document = {
    "_id": ObjectId("69b3ebcea49f1a0e91e56bad"),
    "assay": "coc_v1.0",
    "subtrahend": 199.22,
    "divisor": -41.45,
    "min_allowable_doc_mgl": 0.1,
    "max_allowable_doc_mgl": 40.0,
    "cup_radius_divisor": 3,
    "landscape_xfactor": 2,
    "portrait_xfactor": 1.5,
    "hc_min_distance_pct": 50,
    "hc_param1": 100,
    "hc_param2": 10,
    "hc_min_radius_pct": 8,
    "hc_max_radius_pct": 35,
    "max_offcentre_pct": 20,
    }

    result = collection.insert_one(document)
    print(f"Inserted assay with id: {result.inserted_id}")
    client.close()

if __name__ == '__main__':
    uploaded_images_folder()
    create_assay()