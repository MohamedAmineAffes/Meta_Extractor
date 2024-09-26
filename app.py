import requests
from pymongo import MongoClient
import base64
import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Access the variables
user_access_token = os.getenv('USER_ACCESS_TOKEN')
page_name = os.getenv('PAGE_NAME')


def get_page_access_token_and_id(user_access_token, page_name=None):
    url = "https://graph.facebook.com/v20.0/me/accounts"
    params = {
        "access_token": user_access_token
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        accounts = response.json().get('data', [])

        # If no specific page name is provided, return the first page's token and ID
        if not page_name:
            return accounts[0].get('access_token'), accounts[0].get('id')

        # If a specific page name is provided, find the corresponding token and ID
        for account in accounts:
            if account['name'].lower() == page_name.lower():
                return account.get('access_token'), account.get('id')
        
        print("Page not found.")
        return None, None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching page access token and ID: {e}")
        return None, None

page_token, page_id = get_page_access_token_and_id(user_access_token, page_name=page_name)

url = f"https://graph.facebook.com/v20.0/{page_id}/posts"
parametre = {
    "access_token": page_token,
    "fields": "id,message,full_picture,created_time,comments{message,created_time}",
    "limit": 100  # Adjust the limit as needed
}

def authentication(url,parametre):
    response = requests.get(url, params=parametre)
    return response

# Function to download the image
def download_image(image_url):
    try:
        response = requests.get(image_url)
        if response.status_code == 200:
            return response.content  # Returns binary image data
        else:
            print(f"Failed to download image from {image_url}")
            return None
    except Exception as e:
        print(f"Error fetching image: {e}")
        return None
    
# Function to convert image data to Base64
def image_to_base64(image_data):
    try:
        if image_data:
            return base64.b64encode(image_data).decode('utf-8')  # Converts binary data to Base64 string
        return None
    except Exception as e:
        print(f"Error converting image to Base64: {e}")
        return None

# Function to store the collected data in mongodb    
def store_posts_in_mongodb(posts):
    client = MongoClient("mongodb://localhost:27017/")
    db = client["DemoDB"]
    collection = db["smart_project"]

    documents = []
    for post in posts.get('data', []):
        image_url = post.get("full_picture")
        image_data = download_image(image_url) if image_url else None
        image_base64 = image_to_base64(image_data) if image_data else None

        document = {
            "id": post.get("id"),
            "message": post.get("message"),
            "image_base64": image_base64,
            "created_time": post.get("created_time"),
            "comments": post.get("comments", {}).get("data", [])
        }
        documents.append(document)
    # Check if there are documents to insert
    if documents:
        try:
            collection.insert_many(documents)
            print("Data inserted successfully into MongoDB!")
        except Exception as e:
            print(f"Error inserting data into MongoDB: {e}")
    else:
        print("No data to insert.")

# Function to fetch posts from Facebook Graph API
def fetch_posts_from_facebook(url,parametre):
    response = requests.get(url, params=parametre)
    if response.status_code == 200:
        store_posts_in_mongodb(response.json())
    else:
        print("Error:", response.json())

# Call the function to fetch posts and store them
fetch_posts_from_facebook(url,parametre)  