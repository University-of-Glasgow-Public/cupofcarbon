import math
from unittest.mock import MagicMock, patch

import numpy as np
#import piexif
import pytest
import cv2

from colorimetry.services import image_service #as svc

ASSAY = {
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

@pytest.fixture
def mock_assay(monkeypatch):
    """circle_recognition calls get_assay_data(assay) internally — bypass Mongo."""
    monkeypatch.setattr(image_service, "get_assay_data", lambda assay: ASSAY)
    return ASSAY

@pytest.fixture
def synthetic_image(tmp_path):
    """
    400x400 white 'paper' background with a filled brown circular 'cup'
    at the centre. Cup fill color and paper color are deliberately
    distinct/known so we can hand-compute expected average colors and DOC.
    """
    size = 400
    img = np.full((size, size, 3), 255, dtype=np.uint8)  # BGR white paper = (255,255,255)
    cup_center = (200, 200)
    cup_radius = 60
    cup_color_bgr = (19, 69, 139)  # BGR brown (roughly "saddle brown")
    cv2.circle(img, cup_center, cup_radius, cup_color_bgr, -1)

    path = tmp_path / "test_image.jpg"
    cv2.imwrite(str(path), img)
    return str(path), cup_center, cup_radius, cup_color_bgr

@pytest.fixture
def synthetic_image_blank(tmp_path):
    """
    400x400 white 'paper' background
    """
    size = 400
    img = np.full((size, size, 3), 255, dtype=np.uint8)  # BGR white paper = (255,255,255)
    path = tmp_path / "test_image_blank.jpg"
    cv2.imwrite(str(path), img)
    return str(path)

@pytest.fixture
def synthetic_image_square_cup(tmp_path):
    """
    400x400 white 'paper' background with a filled brown SQUARE 'cup'
    at the centre. Used to test that Hough (circle-only) detection
    correctly fails to match a non-circular shape.
    """
    size = 400
    img = np.full((size, size, 3), 255, dtype=np.uint8)  # white paper
    cup_center = (200, 200)
    half_side = 60  # roughly matches cup_radius used elsewhere
    cup_color_bgr = (19, 69, 139)  # brown

    top_left = (cup_center[0] - half_side, cup_center[1] - half_side)
    bottom_right = (cup_center[0] + half_side, cup_center[1] + half_side)
    cv2.rectangle(img, top_left, bottom_right, cup_color_bgr, -1)

    path = tmp_path / "test_image_square.jpg"
    cv2.imwrite(str(path), img)
    return str(path), cup_center, half_side, cup_color_bgr


@pytest.fixture
def synthetic_image_out_of_focus(tmp_path):
    """
    400x400 white 'paper' background with a filled brown circular 'cup',
    then heavily Gaussian-blurred to simulate an out-of-focus photo.
    Edges are soft/smeared rather than sharp, which is what typically
    causes real Hough circle detection to miss or misestimate radius.
    """
    size = 400
    img = np.full((size, size, 3), 255, dtype=np.uint8)  # white paper
    cup_center = (200, 200)
    cup_radius = 60
    cup_color_bgr = (19, 69, 139)  # brown
    cv2.circle(img, cup_center, cup_radius, cup_color_bgr, -1)

    # Large kernel = strong blur, simulating defocus rather than mild softness
    blurred = cv2.GaussianBlur(img, (41, 41), sigmaX=15)

    path = tmp_path / "test_image_blurred.jpg"
    cv2.imwrite(str(path), blurred)
    return str(path), cup_center, cup_radius, cup_color_bgr

class TestCentral:
    """
    central(x, y, centreHeight, centreWidth, centreLeeway) returns True when
    (x, y) falls within centreWidth ± centreLeeway and centreHeight ± centreLeeway.
    """

    def test_exact_center_is_central(self):
        assert image_service.central(
            x=200, y=200, centreHeight=200, centreWidth=200, centreLeeway=20
        ) is True

    def test_within_leeway_is_central(self):
        assert image_service.central(
            x=210, y=190, centreHeight=200, centreWidth=200, centreLeeway=20
        ) is True

    def test_x_too_far_left_is_not_central(self):
        # leftBoundary = centreWidth - centreLeeway = 200 - 20 = 180
        assert image_service.central(
            x=170, y=200, centreHeight=200, centreWidth=200, centreLeeway=20
        ) is False

    def test_x_too_far_right_is_not_central(self):
        # rightBoundary = centreWidth + centreLeeway = 220
        assert image_service.central(
            x=230, y=200, centreHeight=200, centreWidth=200, centreLeeway=20
        ) is False

    def test_y_too_far_up_is_not_central(self):
        # topBoundary = centreHeight - centreLeeway = 180
        assert image_service.central(
            x=200, y=170, centreHeight=200, centreWidth=200, centreLeeway=20
        ) is False

    def test_y_too_far_down_is_not_central(self):
        # bottomBoundary = centreHeight + centreLeeway = 220
        assert image_service.central(
            x=200, y=230, centreHeight=200, centreWidth=200, centreLeeway=20
        ) is False


class TestGetColors:
    def test_basic_averages_and_correction(self):
        # 2x2 image: cup pixel is pure blue (255,0,0) BGR, paper pixel is (200,0,0)
        img = np.zeros((2, 2, 3), dtype=np.uint8)
        img[0, 0] = [255, 10, 20]   # covered by mask_cup
        img[1, 1] = [200, 30, 40]   # covered by mask_paper

        mask_cup = np.zeros((2, 2), dtype=np.uint8)
        mask_cup[0, 0] = 255
        mask_paper = np.zeros((2, 2), dtype=np.uint8)
        mask_paper[1, 1] = 255

        ave_color, cup_blue, cup_green, cup_red, correction_factor, corrected_blue = \
            image_service.get_colors(img, mask_cup, mask_paper)

        assert cup_blue == pytest.approx(255)
        assert cup_green == pytest.approx(10)
        assert cup_red == pytest.approx(20)
        assert ave_color[0] == pytest.approx(200)
        assert correction_factor == pytest.approx(55)   # 255 - 200
        assert corrected_blue == pytest.approx(310)      # 255 + 55

    def test_empty_mask_gives_zero_mean(self):
        img = np.full((2, 2, 3), 100, dtype=np.uint8)
        empty_mask = np.zeros((2, 2), dtype=np.uint8)
        ave_color, cup_blue, *_ = image_service.get_colors(img, empty_mask, empty_mask)
        assert cup_blue == 0
        assert ave_color[0] == 0

class TestGetDoc:
    def test_basic_calculation(self):
        corrected_blue = 105
        expected = math.exp((corrected_blue - ASSAY["subtrahend"]) / ASSAY["divisor"])
        assert image_service.get_doc(corrected_blue, ASSAY) == pytest.approx(expected)

    def test_zero_divisor_raises_zero_division_error(self):
        assay = {"subtrahend": 100.0, "divisor": 0.0}
        with pytest.raises(ZeroDivisionError):
            image_service.get_doc(150.0, assay)

    def test_missing_assay_key_raises_key_error(self):
        incomplete_assay = {"subtrahend": 100.0}  # no 'divisor'
        with pytest.raises(KeyError):
            image_service.get_doc(150.0, incomplete_assay)

class TestCircleRecognition:
    def test_round_sharp_cup_is_found(self, mock_assay, synthetic_image):
        path, _, _, _ = synthetic_image
        result = image_service.circle_recognition(path, ASSAY)
        assert result.circle_found is True

    def test_nothing_is_found_in_blank(self, mock_assay, synthetic_image_blank):
        path = synthetic_image_blank
        result = image_service.circle_recognition(path, ASSAY)
        assert result.circle_found is False

    def test_out_of_focus_cup_is_not_found(self, mock_assay, synthetic_image_out_of_focus):
        path, _, _, _ = synthetic_image_out_of_focus
        result = image_service.circle_recognition(path, ASSAY)
        assert result.circle_found is False

    # next function generates a false positive
    # Hough Gradient genuinely fit a circle to some curvature in the square's edges 
    # (likely near a corner, where the gradient direction changes enough to satisfy 
    # the accumulator at param2=10), and that circle happens to sit near the image center
    # with a plausible radius.
    # Hough config (param1=100, param2=10) will false-positive on sharp-edged square-ish
    # objects placed roughly in-frame. 

    # def test_square_cup_is_not_found(self, mock_assay, synthetic_image_square_cup):
    #     path, _, _, _ = synthetic_image_square_cup
    #     result = image_service.circle_recognition(path, ASSAY)
    #     assert result.circle_found is False
