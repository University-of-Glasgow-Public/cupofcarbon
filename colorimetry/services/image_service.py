""" Image related functions """
import math
from pathlib import Path
import cv2
import numpy as np
from PIL.ExifTags import TAGS, GPSTAGS
from colorimetry.image.models import CircleData
from colorimetry.services.query_service import get_assay_data
import piexif

# A4 in millimetres
A4_W_MM, A4_H_MM = 210.0, 297.0
# printed size of the black square
ARUCO_SIZE_MM = 20.0   
# marker inset from TL edges (for single-marker workflows)
INSET_X_MM, INSET_Y_MM = 10.0, 10.0  

# Choose dictionary (matches the PDF I generated: DICT_4X4_50)
ARUCO_DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

def _ensure_image(image_or_path):
    """Return a BGR numpy image from either a path or an already-loaded ndarray."""
    if isinstance(image_or_path, (str, Path)):
        p = Path(image_or_path)
        if not p.exists():
            raise FileNotFoundError(f"Image path not found: {p}")
        img = cv2.imread(str(p), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"cv2.imread failed for: {p}. "
                             "Check path, permissions, or file integrity.")
        return img
    if isinstance(image_or_path, np.ndarray):
        if image_or_path.ndim == 2:
            # Gray -> convert to BGR for consistency
            return cv2.cvtColor(image_or_path, cv2.COLOR_GRAY2BGR)
        elif image_or_path.ndim == 3:
            return image_or_path
        else:
            raise TypeError("Unsupported ndarray shape for image.")
    else:
        raise TypeError("image_or_path must be a file path or numpy.ndarray")

def crop_a4_with_aruco(image_or_path, out_dpi=300, expected_ids=(0,1,2,3)):
    """
    Detect ArUco markers, compute homography to an A4 canvas, and return rectified image.
    - image_or_path: path or ndarray (BGR)
    - out_dpi: controls output canvas resolution (affects only the rectified image size)
    - expected_ids: IDs placed at TL, TR, BR, BL (used for optional verification)
    """
    image_bgr = _ensure_image(image_or_path)
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    # --- Detect markers (API differences across OpenCV versions) ---
    # Newer OpenCV (>= 4.7) has cv2.aruco.ArucoDetector
    if hasattr(cv2.aruco, "ArucoDetector"):
        params = cv2.aruco.DetectorParameters()
        detector = cv2.aruco.ArucoDetector(ARUCO_DICT, params)
        corners, ids, _ = detector.detectMarkers(gray)
    else:
        # Older API
        params = cv2.aruco.DetectorParameters_create()
        corners, ids, _ = cv2.aruco.detectMarkers(gray,
                                                  ARUCO_DICT, parameters=params)

    if ids is None or len(ids) == 0:
        raise RuntimeError("No ArUco markers detected.")

    # For robustness, use all detected marker corners against their known positions.
    # Here we know tag IDs and that tags sit in the four corners, inset by 10 mm,
    # with 20 mm size. We’ll define the outer black square corners in design coords.

    # Mapping: TL=0, TR=1, BR=2, BL=3 by design (adjust if your PDF used different IDs)
    id_to_corner_name = {expected_ids[0]: "TL",
                         expected_ids[1]: "TR",
                         expected_ids[2]: "BR",
                         expected_ids[3]: "BL"}

    # Design positions (top-left origin, x right, y down)
    def square_corners_mm(x_mm, y_mm, size_mm):
        # TL, TR, BR, BL
        return np.array([
            [x_mm,           y_mm          ],
            [x_mm + size_mm, y_mm          ],
            [x_mm + size_mm, y_mm + size_mm],
            [x_mm,           y_mm + size_mm],
        ], dtype=np.float32)

    design_tag_corners = {
        "TL": square_corners_mm(INSET_X_MM, INSET_Y_MM, ARUCO_SIZE_MM),
        "TR": square_corners_mm(A4_W_MM - INSET_X_MM - ARUCO_SIZE_MM,
                                INSET_Y_MM, ARUCO_SIZE_MM),
        "BR": square_corners_mm(A4_W_MM - INSET_X_MM - ARUCO_SIZE_MM,
                                A4_H_MM - INSET_Y_MM - ARUCO_SIZE_MM, ARUCO_SIZE_MM),
        "BL": square_corners_mm(INSET_X_MM,
                                A4_H_MM - INSET_Y_MM - ARUCO_SIZE_MM, ARUCO_SIZE_MM),
    }

    img_pts = []
    des_pts = []

    ids = ids.flatten()
    for corner_arr, tag_id in zip(corners, ids):
        if tag_id in id_to_corner_name:
            name = id_to_corner_name[tag_id]
            # corner_arr shape: (1, 4, 2) in order TL, TR, BR, BL
            img_c = corner_arr.reshape(-1, 2).astype(np.float32)
            des_c = design_tag_corners[name]
            img_pts.append(img_c)
            des_pts.append(des_c)

    if len(img_pts) == 0:
        raise RuntimeError("Expected tag IDs not found among detections.")
    # Nx2
    img_pts = np.concatenate(img_pts, axis=0)  
    # Nx2
    des_pts = np.concatenate(des_pts, axis=0)  

    # Compute homography (image -> design in mm units)
    H_img_to_design, mask = cv2.findHomography(img_pts, des_pts,
                                               method=cv2.RANSAC, ransacReprojThreshold=3.0)
    if H_img_to_design is None:
        raise RuntimeError("Homography estimation failed.")

    # Prepare canvas size from desired DPI
    px_per_mm = out_dpi / 25.4
    out_w = int(round(A4_W_MM * px_per_mm))
    out_h = int(round(A4_H_MM * px_per_mm))

    S = np.array([[px_per_mm, 0, 0],
                  [0, px_per_mm, 0],
                  [0, 0, 1]], dtype=np.float32)

    H_img_to_canvas = S @ H_img_to_design

    rectified = cv2.warpPerspective(image_bgr, H_img_to_canvas,
                                    (out_w, out_h), flags=cv2.INTER_LINEAR)
    return rectified


def get_cropped_image(img_file_path):
    rectified = crop_a4_with_aruco(img_file_path)
    cropped_file = "cropped_file.jpg"
    cv2.imwrite(cropped_file, rectified)
    return cropped_file


def central(x, y, centreHeight, centreWidth, centreLeeway):
    leftBoundary = centreWidth - centreLeeway
    rightBoundary = centreWidth + centreLeeway
    topBoundary = centreHeight - centreLeeway
    bottomBoundary = centreHeight + centreLeeway
    if x < leftBoundary or x > rightBoundary or y < topBoundary or y > bottomBoundary:
        # print("Circle is not central!")
        return False
    else:
        # print("Circle is central!")
        return True

def get_circle_values(dimensions, assay):
    centreHeight = int(dimensions[0] / 2)
    centreWidth = int(dimensions[1] / 2)
    maxCupRadius = dimensions[1] / (100/assay['hc_max_radius_pct'])
    minCupRadius = dimensions[1] / (100/assay['hc_min_radius_pct'])
    minDistance = dimensions[1] / (100/assay['hc_min_distance_pct'])
    centreLeeway = dimensions[1] / (100/assay['max_offcentre_pct'])
    return centreHeight, centreWidth, maxCupRadius, minCupRadius, minDistance, centreLeeway

def get_colors(img,mask_cup, mask_paper):
    # get average blue, green and red color with mask
    ave_color = cv2.mean(img, mask=mask_cup)[:3]
    # Blue
    cup_blue = ave_color[0]  
    # Green
    cup_green = ave_color[1] 
    # Red
    cup_red = ave_color[2] 

    ## Look at img but only where mask_paper is white
    ave_color = cv2.mean(img, mask=mask_paper)[:3]
    # paper's blue channel as a white reference.
    correction_factor = 255 - ave_color[0]

    # Adjust cup blue value.
    corrected_blue = cup_blue + correction_factor

    return ave_color, cup_blue, cup_green, cup_red, correction_factor, corrected_blue

def get_doc(corrected_blue, assay):
    doc = math.exp((corrected_blue - assay['subtrahend']) / assay['divisor'])
    return doc

def visualize(img, assay, mask_cup, mask_paper, x,y,r):
    output = img.copy()
    # cv2.circle(image to draw on, (x, y), circleradius, color(B,G,R), thickness) if thickness=-1 fills the circle
    # Not used in calculation, only for image creating
    # Draws cup border green
    cv2.circle(output, (x, y), r,
                (0, 255, 0), 2)  
    # Draws red point a centre
    cv2.circle(output, (x, y), 2,
                (0, 0, 255), 3)  
    # Drwas sample region in cup
    cv2.circle(output, (x, y), int(r / assay['cup_radius_divisor']),
                (0, 255, 0), 2)  
    # Drwas paper refrence region
    cv2.circle(output, (x, int(y + (assay['portrait_xfactor'] * r))),
                int(r / assay['cup_radius_divisor']), (0, 255, 0), 2)    
    BASE_DIR = Path(__file__).resolve().parent.parent
    upload_dir = BASE_DIR / "static" / "uploaded_images"
    cv2.imwrite(str(upload_dir / "circle_detection.jpg"))
    cv2.imwrite(str(upload_dir / "mask_cup.jpg"), mask_cup)
    cv2.imwrite(str(upload_dir / "mask_paper.jpg"), mask_paper)

def circle_recognition(img_path, assay):
    # Read image
    img = cv2.imread(img_path)
    dimensions = img.shape
    circles_found = False
    assay = get_assay_data(assay)

    centreHeight, centreWidth, maxCupRadius, minCupRadius, minDistance, centreLeeway = get_circle_values(dimensions, assay)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Reduce noise
    gray = cv2.medianBlur(gray, 5)

    # Detect circles
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=int(round(minDistance)),
        param1=assay['hc_param1'],
        param2=assay['hc_param2'],
        minRadius=int(round(minCupRadius)),
        maxRadius=int(round(maxCupRadius))
    )

    #creates circle object to store values
    circle_data = CircleData()

    #if not circle was detected
    if circles is None:
        circle_data.circle_found = circles_found
        return circle_data

    # Draw only the first detected circle
    circles = np.uint16(np.around(circles))
    for circle in circles[0]:
        x, y, r = circle
        if central(x, y, centreHeight, centreWidth, centreLeeway):
            circles_found = True
            break

    #if not central circle
    if not circles_found:
        circle_data.circle_found = circles_found
        return circle_data

    # Black Mask
    mask_cup = np.zeros_like(gray)  
    # Black Mask
    mask_paper = np.zeros_like(gray)       
    # cv2.circle(image to draw on, (x, y), circleradius, color(B,G,R), thickness) if thickness=-1 fills the circle
    # Creates a filled white region inside cup
    cv2.circle(mask_cup, (x, y), int(r / assay['cup_radius_divisor']),
                (255, 255, 255), -1)
    # Creates a filledwhite region in paper
    cv2.circle(mask_paper, (x, int(y + (assay['portrait_xfactor'] * r))),
                int(r / assay['cup_radius_divisor']), 255, -1)     

    #visualize(img, assay, mask_cup, mask_paper, x, y, r)


    ave_color, cup_blue, cup_green, cup_red, correction_factor, corrected_blue = get_colors(img, mask_cup, mask_paper)

    doc = get_doc(corrected_blue, assay)

    max_al_doc = assay['max_allowable_doc_mgl']
    min_al_doc = assay['min_allowable_doc_mgl']

    circle_data.circle_found = circles_found
    if doc > max_al_doc:
        circle_data.doc = f">{max_al_doc}"
    elif doc < min_al_doc:
        circle_data.doc = f"<{min_al_doc}>"
    else:
        circle_data.doc = round(doc, 2)
    circle_data.cup_blue = round(cup_blue, 2)
    circle_data.cup_green = round(cup_green, 2)
    circle_data.cup_red = round(cup_red, 2)
    circle_data.paper_blue = round(ave_color[0], 2)
    circle_data.paper_green = round(ave_color[1], 2)
    circle_data.paper_red = round(ave_color[2], 2)

    return circle_data


def extract_exif(image):
    exif_data = {}

    exif_bytes = image.info.get("exif")
    if not exif_bytes:
        return {}

    exif_dict = piexif.load(exif_bytes)

    exif_data['LocationFound'] = False
    exif_data['ExifDateTime'] = None

    exif_section = exif_dict.get("Exif", {})
    zeroth_section = exif_dict.get("0th", {})

    date_fields = [
        exif_section.get(piexif.ExifIFD.DateTimeOriginal),
        exif_section.get(piexif.ExifIFD.DateTimeDigitized),
        zeroth_section.get(piexif.ImageIFD.DateTime),
    ]

    for dt in date_fields:
        if dt:
            exif_data["ExifDateTime"] = dt.decode()
            break

    gps = exif_dict.get("GPS", {})
    if gps:
        def to_decimal(values):
            try:
                if not values or len(values) != 3:
                    return None

                def safe_div(x):
                    num, den = x
                    if den == 0:
                        return None
                    return num / den

                d = safe_div(values[0])
                m = safe_div(values[1])
                s = safe_div(values[2])

                if None in (d, m, s):
                    return None

                return d + (m / 60.0) + (s / 3600.0)

            except (TypeError, IndexError, ZeroDivisionError):
                return None

        lat = gps.get(piexif.GPSIFD.GPSLatitude)
        lat_ref = gps.get(piexif.GPSIFD.GPSLatitudeRef)
        lon = gps.get(piexif.GPSIFD.GPSLongitude)
        lon_ref = gps.get(piexif.GPSIFD.GPSLongitudeRef)

        if lat and lat_ref and lon and lon_ref:
            try:
                lat = to_decimal(lat)
                lon = to_decimal(lon)

                if lat is not None and lon is not None:
                    if lat_ref == b"S":
                        lat = -lat
                    if lon_ref == b"W":
                        lon = -lon

                    exif_data["Latitude"] = lat
                    exif_data["Longitude"] = lon
                    exif_data['LocationFound'] = True
            except Exception:
                pass

    return exif_data
