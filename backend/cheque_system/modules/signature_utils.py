import os
import cv2


def remove_empty_borders(binary_img):
    coords = cv2.findNonZero(binary_img)

    if coords is None:
        return binary_img

    x, y, w, h = cv2.boundingRect(coords)
    return binary_img[y:y + h, x:x + w]


def preprocess_signature(signature_img):
    gray = cv2.cvtColor(signature_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    _, binary = cv2.threshold(
        gray,
        180,
        255,
        cv2.THRESH_BINARY_INV
    )

    binary = remove_empty_borders(binary)

    binary = cv2.resize(
        binary,
        (400, 160),
        interpolation=cv2.INTER_AREA
    )

    return binary


def signature_template_score(signature_crop, reference_signature):
    sig1 = preprocess_signature(signature_crop)
    sig2 = preprocess_signature(reference_signature)

    result = cv2.matchTemplate(sig1, sig2, cv2.TM_CCOEFF_NORMED)
    score = float(result.max())

    if score < 0:
        score = 0.0

    return round(score, 3)


def signature_orb_score(signature_crop, reference_signature):
    sig1 = preprocess_signature(signature_crop)
    sig2 = preprocess_signature(reference_signature)

    orb = cv2.ORB_create(nfeatures=1500)

    kp1, des1 = orb.detectAndCompute(sig1, None)
    kp2, des2 = orb.detectAndCompute(sig2, None)

    if des1 is None or des2 is None:
        return 0.0

    if len(kp1) == 0 or len(kp2) == 0:
        return 0.0

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = matcher.match(des1, des2)

    if not matches:
        return 0.0

    good_matches = [m for m in matches if m.distance < 65]

    score = len(good_matches) / max(len(kp1), len(kp2), 1)

    return round(float(score), 3)


def signature_similarity(signature_crop, reference_signature):
    template_score = signature_template_score(signature_crop, reference_signature)
    orb_score = signature_orb_score(signature_crop, reference_signature)

    final_score = (template_score * 0.75) + (orb_score * 0.25)

    return {
        "template_score": template_score,
        "orb_score": orb_score,
        "final_score": round(final_score, 3)
    }


def verify_signature(signature_crop, client):
    if not client:
        return {
            "is_correct": False,
            "status": "client_introuvable",
            "score": 0,
            "template_score": 0,
            "orb_score": 0,
            "message": "Client introuvable, impossible de vérifier la signature."
        }

    signature_path = client["signature_path"]

    if not os.path.exists(signature_path):
        return {
            "is_correct": False,
            "status": "signature_reference_absente",
            "score": 0,
            "template_score": 0,
            "orb_score": 0,
            "message": "Signature de référence introuvable."
        }

    reference_signature = cv2.imread(signature_path)

    if reference_signature is None:
        return {
            "is_correct": False,
            "status": "signature_reference_invalide",
            "score": 0,
            "template_score": 0,
            "orb_score": 0,
            "message": "Impossible de lire la signature de référence."
        }

    scores = signature_similarity(signature_crop, reference_signature)
    final_score = scores["final_score"]

    if final_score >= 0.45:
        status = "probablement_correcte"
        message = "Signature probablement correcte."
        is_correct = True
    elif final_score >= 0.25:
        status = "a_verifier"
        message = "Signature incertaine, vérification manuelle recommandée."
        is_correct = False
    else:
        status = "differente"
        message = "Signature probablement différente."
        is_correct = False

    return {
        "is_correct": is_correct,
        "status": status,
        "score": final_score,
        "template_score": scores["template_score"],
        "orb_score": scores["orb_score"],
        "message": message
    }