#!/usr/bin/python3
import os
# import hashlib
import json
import logging
# import pickle
# import io
# non-std
# import requests
import boto3
# import yaml
# non-std modules installed by pip
# import googleapiclient
from googleapiclient.discovery import build
# from google_auth_oauthlib.flow import InstalledAppFlow
# from google.auth.transport.requests import Request
# from apiclient import http
# own modules
from webstorageS3 import FileStorageClient
from tools import get_credentials, get_ids, put_metadata, put_filestorage, download_media
# from tools import *


SCOPES = os.environ["SCOPES"]  # scopes
TOKEN_FILE = os.environ["TOKEN_FILE"]  # pickled token
SECRETS_FILE = os.environ["SECRETS_FILE"]  # google credentials
TMP_FILENAME = os.environ["TMP_FILENAME"]  # name of temporary file
BUCKET_NAME = os.environ["BUCKET_NAME"]
AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
ENDPOINT_URL = os.environ["ENDPOINT_URL"]


# setting Logging
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
if LOG_LEVEL == "INFO":
    logging.getLogger().setLevel(logging.INFO)

if LOG_LEVEL == "ERROR":
    logging.getLogger().setLevel(logging.ERROR)

if LOG_LEVEL == "DEBUG":
    logging.getLogger().setLevel(logging.DEBUG)


def main():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = get_credentials(TOKEN_FILE, SCOPES, SECRETS_FILE)
    stats = {
        "analyzed": 0,
        "copied": 0,
        "skipped": 0,
        "empty": 0
    }
    # for api documentation go to https://developers.google.com/photos/library/reference/rest/v1/mediaItems/list
    service = build('photoslibrary', 'v1', credentials=creds)
    results = service.mediaItems().list().execute()
    items = results.get('mediaItems', [])
    if not items:
        logging.info('No items found.')
    else:
        fs = FileStorageClient(cache=False)  # global filestorage
        client = boto3.client(  # global s3 target
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            endpoint_url=ENDPOINT_URL
        )
        logging.info("getting stored ids")
        local_ids = get_ids(client, BUCKET_NAME)
        logging.info(f"there are {len(local_ids)} items already stored in FileStorage")
        logging.info("iterating over photos")
        while results.get("nextPageToken"):  # as long as there are more pages
            for item in items:
                try:
                    logging.debug(json.dumps(item, indent=4))
                    # {
                    #    "id": "AMcb8COTk5ouJwMz7KugvmXNCSH-pCoAg4FqJSkHgOZWYkVNcDwySF6N5kSoDvDWr9tdkX7cMORMDgbiPdOjNMCqTUU7RaEdpA",
                    #    "productUrl": "https://photos.google.com/lr/photo/AMcb8COTk5ouJwMz7KugvmXNCSH-pCoAg4FqJSkHgOZWYkVNcDwySF6N5kSoDvDWr9tdkX7cMORMDgbiPdOjNMCqTUU7RaEdpA",
                    #    "baseUrl": ".... some long url ...",
                    #    "mimeType": "image/jpeg",
                    #    "mediaMetadata": {
                    #        "creationTime": "2020-09-05T15:56:39Z",
                    #        "width": "4160",
                    #        "height": "3120",
                    #        "photo": {
                    #            "cameraMake": "motorola",
                    #            "cameraModel": "Moto G (5)",
                    #            "focalLength": 3.59,
                    #            "apertureFNumber": 2,
                    #            "isoEquivalent": 1600
                    #        }
                    #    },
                    #    "filename": "IMG_20200905_175639247.jpg"
                    # }
                    stats["analyzed"] += 1
                    if item['id'] in local_ids:
                        stats["skipped"] += 1
                        logging.info(f"skipping already stored {item['id']} - {item['filename']}")
                        continue
                    if item["mediaMetadata"].get("photo"):
                        logging.info(f"analyzing {item['id']} - {item['filename']}")
                        # TMP_FILENAME = f"/home/mesznera/Bilder/photos-sync/{item['filename']}"
                        # go to
                        # https://developers.google.com/photos/library/guides/access-media-items#base-urls
                        # for baseUrl handling
                        # works only for photos
                        base_url = f"{item['baseUrl']}=w{item['mediaMetadata']['width']}-h{item['mediaMetadata']['height']}-d"
                        with open(TMP_FILENAME, "wb") as outfile:
                            download_media(base_url, outfile)
                        with open(TMP_FILENAME, "rb") as infile:
                            item["sha1Checksum"] = put_filestorage(fs, infile)
                        put_metadata(client, BUCKET_NAME, item)
                    elif item["mediaMetadata"].get("video"):
                        logging.info(f"analyzing {item['id']} - {item['filename']}")
                        # TMP_FILENAME = f"/home/mesznera/Videos/photos-sync/{item['filename']}"
                        # go to
                        # https://developers.google.com/photos/library/guides/access-media-items#base-urls
                        # for baseUrl handling
                        # works only for videos
                        base_url = f"{item['baseUrl']}=dv"
                        with open(TMP_FILENAME, "wb") as outfile:
                            download_media(base_url, outfile)
                        with open(TMP_FILENAME, "rb") as infile:
                            item["sha1Checksum"] = put_filestorage(fs, infile)
                        put_metadata(client, BUCKET_NAME, item)
                    else:
                        stats["skipped"] += 1
                        logging.info(f"skipping non photo nor video {item['id']} - {item['filename']}")
                        logging.debug(json.dumps(item, indent=4))
                        continue
                except Exception as exc:
                    logging.exception(exc)
                    logging.debug(json.dumps(item, indent=4))
                    raise exc
            logging.debug("Getting next page")
            results = service.mediaItems().list(pageToken=results.get("nextPageToken")).execute()
            items = results.get("mediaItems", [])
    logging.debug(json.dumps(stats, indent=4))


if __name__ == '__main__':
    main()
