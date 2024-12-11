from flask import Flask, request, jsonify
import cv2
import numpy as np
import requests
import boto3
import os
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

# Configure AWS S3
AWS_ACCESS_KEY = "<YOUR_AWS_ACCESS_KEY>"
AWS_SECRET_KEY = "<YOUR_AWS_SECRET_KEY>"
S3_BUCKET = "<YOUR_BUCKET_NAME>"
s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)

def upload_to_s3(file_path, object_name):
    """Uploads a file to S3 and returns the public URL."""
    try:
        s3_client.upload_file(file_path, S3_BUCKET, object_name, ExtraArgs={"ACL": "public-read"})
        return f"https://{S3_BUCKET}.s3.amazonaws.com/{object_name}"
    except Exception as e:
        raise RuntimeError(f"S3 upload failed: {e}")

def remove_background(image_url, bounding_box):
    """Processes the image and removes the background for the specified bounding box."""
    response = requests.get(image_url, stream=True)
    if response.status_code != 200:
        raise ValueError("Invalid image URL or failed to fetch the image.")

    # Load image from URL
    img_array = np.asarray(bytearray(response.content), dtype=np.uint8)
    image = cv2.imdecode(img_array, cv2.IMREAD_UNCHANGED)

    if image is None:
        raise ValueError("Failed to decode the image.")

    # Extract bounding box
    x_min, y_min, x_max, y_max = bounding_box
    if x_min >= x_max or y_min >= y_max or x_max > image.shape[1] or y_max > image.shape[0]:
        raise ValueError("Invalid bounding box coordinates.")

    # Create mask for background removal
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    mask[y_min:y_max, x_min:x_max] = 255

    # Apply mask
    result = cv2.bitwise_and(image, image, mask=mask)
    result[mask == 0] = [0, 0, 0, 0]  # Ensure transparency for removed areas

    # Save processed image locally
    output_path = "processed_image.png"
    cv2.imwrite(output_path, result)

    # Upload to S3 and get URL
    processed_url = upload_to_s3(output_path, "processed_image.png")

    # Cleanup local file
    os.remove(output_path)

    return processed_url

@app.route('/remove-background', methods=['POST'])
def remove_background_api():
    try:
        data = request.json
        if not data or 'image_url' not in data or 'bounding_box' not in data:
            return jsonify({"error": "Invalid input. Please provide 'image_url' and 'bounding_box'."}), 400

        image_url = data['image_url']
        bounding_box = data['bounding_box']

        if not all(k in bounding_box for k in ('x_min', 'y_min', 'x_max', 'y_max')):
            return jsonify({"error": "Bounding box must include 'x_min', 'y_min', 'x_max', 'y_max'."}), 400

        processed_url = remove_background(image_url, [
            bounding_box['x_min'],
            bounding_box['y_min'],
            bounding_box['x_max'],
            bounding_box['y_max']
        ])

        return jsonify({
            "original_image_url": image_url,
            "processed_image_url": processed_url
        })
    except HTTPException as http_err:
        return jsonify({"error": str(http_err)}), http_err.code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
