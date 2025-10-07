import cv2
import numpy as np
import pyzbar.pyzbar as qr
import mediapipe as mp
import joblib
import pandas as pd  
from src.module.audioPlayer import CommandAudioPlayer

#Initilize camera and set pipeline configuration.
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
font = cv2.FONT_HERSHEY_COMPLEX

# Real width of the QR code (cm) (adjust if you use different size)
QR_REAL_WIDTH = 8.5
# Focal length (in pixels) of your camera (adjust if you use different camera)
FOCAL_LENGTH = 1411
# Maximum distance for drawing (cm)
MAX_DISTANCE_CM = 150


# smooth factor improves stability of distance measurement, reducing jitter ( optional )
# (0 = no smoothing, 1 = max smoothing but laggy)
USE_SMOOTHING = True
SMOOTH_ALPHA = 0.3 
_smooth_distance = None 

_camera_matrix = None
_dist_coeffs = np.zeros((5,1), dtype=np.float32)

def _order_square_points(pts_img):
    """Order 4 points (x,y) consistently: top-left, top-right, bottom-right, bottom-left."""
    pts = np.array(pts_img, dtype=np.float32)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).reshape(-1)
    ordered = np.zeros((4,2), dtype=np.float32)
    ordered[0] = pts[np.argmin(s)]  # top-left
    ordered[2] = pts[np.argmax(s)]  # bottom-right
    ordered[1] = pts[np.argmin(diff)]  # top-right
    ordered[3] = pts[np.argmax(diff)]  # bottom-left
    return ordered

def _rotation_matrix_to_euler_xyz(R):
    """Convert rotation matrix to euler XYZ (roll, pitch, yaw)."""
    sy = np.sqrt(R[0,0]*R[0,0] + R[1,0]*R[1,0])
    singular = sy < 1e-6
    if not singular:
        roll = np.degrees(np.arctan2(R[2,1], R[2,2]))      # X
        pitch = np.degrees(np.arctan2(-R[2,0], sy))        # Y
        yaw = np.degrees(np.arctan2(R[1,0], R[0,0]))       # Z
    else:
        roll = np.degrees(np.arctan2(-R[1,2], R[1,1]))
        pitch = np.degrees(np.arctan2(-R[2,0], sy))
        yaw = 0.0
    return roll, pitch, yaw

def _compute_pitch_deg(polygon_points, frame_shape):
    """estimate the inclination (pitch) of the camera relative to the QR code."""
    global _camera_matrix
    if polygon_points is None or len(polygon_points) < 4:
        return None
    pts = np.array([[p.x, p.y] for p in polygon_points], dtype=np.float32)
    if pts.shape[0] != 4:
        return None
    h, w = frame_shape[:2]
    if _camera_matrix is None:
        cx, cy = w/2.0, h/2.0
        _camera_matrix = np.array([[FOCAL_LENGTH, 0, cx], [0, FOCAL_LENGTH, cy], [0,0,1]], dtype=np.float32)
    img_pts = _order_square_points(pts)
    obj_pts = np.array([
        [0, 0, 0],
        [QR_REAL_WIDTH, 0, 0],
        [QR_REAL_WIDTH, QR_REAL_WIDTH, 0],
        [0, QR_REAL_WIDTH, 0]
    ], dtype=np.float32)
    ok, rvec = cv2.solvePnP(obj_pts, img_pts, _camera_matrix, _dist_coeffs, flags=cv2.SOLVEPNP_IPPE_SQUARE)
    if not ok:
        return None
    R, _ = cv2.Rodrigues(rvec)
    pitch = _rotation_matrix_to_euler_xyz(R)
    
    return pitch

def demo(dir_audio):
    # initialize audio player.
    player = CommandAudioPlayer(dir_audio)
    global _smooth_distance
    # Check if the camera opened successfully
    if not cap.isOpened():
            raise RuntimeError("Camera not found or not available", 500)
        
# Main loop
    while True:
        ret, cuadro = cap.read()
        detectedQr = qr.decode(cuadro)
        commandQr = None
        if not ret:
            raise RuntimeError("Failed to read frame from camera", 500)

        ## Process the Qr code detected open cv2 only executes squarer chasing if there is a Qr code detected.
        for obj in detectedQr:
            command_from_qr = obj.data.decode('utf-8') if obj.data else ''
            
            ## limit the data length to avoid overflow
            qr_width_in_px = max(1, obj.rect.width)
            raw_distance = (QR_REAL_WIDTH * FOCAL_LENGTH) / qr_width_in_px

            ## apply smoothing filter to distance
            if USE_SMOOTHING and _smooth_distance is not None:
                distance_cm = SMOOTH_ALPHA * raw_distance + (1 - SMOOTH_ALPHA) * _smooth_distance
            else:
                distance_cm = raw_distance
            ## compute the pitch angle relative to the QR code to know if the camera is tilted.( its optional )
            pitch_angle = _compute_pitch_deg(obj.polygon, cuadro.shape)


            ## What if the virtual mocked distance is more than the max distance?
            if distance_cm <= MAX_DISTANCE_CM:
                cv2.rectangle(
                    cuadro,
                    (obj.rect.left, obj.rect.top),
                    (obj.rect.left + obj.rect.width, obj.rect.top + obj.rect.height),
                    (0, 255, 0),
                    3
                )
                commandQr = command_from_qr
                ## draw the squarer green around the Qr and also the pitch angle. use the pitch angle to make decisions for further control.
                cv2.putText(cuadro, command_from_qr, (obj.rect.left, max(15, obj.rect.top - 10)), font, 1, (0, 255, 0), 2)
                cv2.putText(cuadro, f"Dist: {distance_cm:.1f} cm", (obj.rect.left, obj.rect.top + obj.rect.height + 20), font, 1, (0, 255, 0), 2)
                if pitch_angle is not None:
                    cv2.putText(cuadro, f"Pitch: {pitch_angle:.1f} g", (obj.rect.left, obj.rect.top + 50), font, 0.6, (0, 255, 0), 2)
            else:
                ## draw the squarer red around the Qr.
                cv2.rectangle(cuadro,(obj.rect.left, obj.rect.top),(obj.rect.left + obj.rect.width, obj.rect.top + obj.rect.height),(0, 0, 255),3)
                cv2.putText(cuadro, "Fuera de rango", (obj.rect.left, max(15, obj.rect.top - 10)), font, 1, (0, 0, 255), 2)
                commandQr = None
        
        ## Send the extracted and processed image data to any motion service.
        ## Example:
        ## - motor-device services 
        ## - middlewares to make second plane decisions
        ## - External Api's
        ## - Url Ux treatment.
        
        player.process_command(commandQr)
        
        
cap.release()
    
