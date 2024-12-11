

import requests

url = "http://127.0.0.1:5000/remove-background"
data = {
    "image_url": "https://example.com/path/to/image.jpg",
    "bounding_box": {
        "x_min": 50,
        "y_min": 50,
        "x_max": 200,
        "y_max": 200
    }
}

response = requests.post(url, json=data)

if response.status_code == 200:
    print("Processed Image URL:", response.json()["processed_image_url"])
else:
    print("Error:", response.json())
