#!/usr/bin/python3
"""
program to sync google foto items to local S3 storage
isung FileStorageClient
"""

import json
import logging
import os
import time

# non-std
import boto3

# import googleapiclient
from googleapiclient.discovery import build
from prometheus_client import start_http_server, Gauge, Summary

# own modules
from webstorageS3 import FileStorageClient
from tools import (
    get_credentials,
    get_ids,
    put_metadata,
    put_filestorage,
    download_media,
)

logging.basicConfig(level=logging.INFO)

APP_SCOPES = os.environ["APP_SCOPES"]  # scopes
APP_TOKEN_FILE = os.environ["APP_TOKEN_FILE"]  # pickled token
APP_SECRETS_FILE = os.environ["APP_SECRETS_FILE"]  # google credentials
APP_BUCKET_NAME = os.environ["APP_BUCKET_NAME"]
APP_AWS_ACCESS_KEY_ID = os.environ["APP_AWS_ACCESS_KEY_ID"]
APP_AWS_SECRET_ACCESS_KEY = os.environ["APP_AWS_SECRET_ACCESS_KEY"]
APP_ENDPOINT_URL = os.environ["APP_ENDPOINT_URL"]
# with default values
APP_TMP_FILENAME = os.environ.get(
    "APP_TMP_FILENAME", "/usr/src/app/data/tmp.dmp"
)  # name of temporary file
APP_INTERVAL = int(
    os.environ.get("APP_INTERVAL", "86400")
)  # interval in seconds to do the sync
APP_LOG_LEVEL = os.environ.get("APP_LOG_LEVEL", "INFO")

# setting Logging
APP_LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
if APP_LOG_LEVEL == "INFO":
    logging.getLogger().setLevel(logging.INFO)

if APP_LOG_LEVEL == "ERROR":
    logging.getLogger().setLevel(logging.ERROR)

if APP_LOG_LEVEL == "DEBUG":
    logging.getLogger().setLevel(logging.DEBUG)

for key, value in os.environ.items():
    if key.startswith("APP_"):
        logging.info(f"{key} : {value}")


# prometheus metrics
SUMMARY = Summary("fotos_sync_processing_seconds", "Time spent processing a sync")
STATS = {
    "analyzed": Gauge("fotos_sync_analyzed", "Number of analyzed objects"),
    "copied": Gauge("fotos_sync_copied", "Number of downloaded objects"),
    "skipped": Gauge("fotos_sync_skipped", "Number of skipped objects"),
    "error": Gauge("fotos_sync_error", "Number of objects where errors occured"),
    "empty": Gauge("fotos_sync_empty", "Number empty objects, they are skipped"),
}


@SUMMARY.time()
def main():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = get_credentials(APP_TOKEN_FILE, APP_SCOPES, APP_SECRETS_FILE)
    stats = {"analyzed": 0, "copied": 0, "skipped": 0, "empty": 0}
    # for api documentation go to https://developers.google.com/photos/library/reference/rest/v1/mediaItems/list
    service = build("photoslibrary", "v1", credentials=creds, static_discovery=False)
    results = service.mediaItems().list().execute()
    items = results.get("mediaItems", [])
    if not items:
        logging.info("No items found.")
    else:
        fs = FileStorageClient(cache=False)  # global filestorage
        client = boto3.client(  # global s3 target
            "s3",
            aws_access_key_id=APP_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=APP_AWS_SECRET_ACCESS_KEY,
            endpoint_url=APP_ENDPOINT_URL,
        )
        logging.info("getting stored ids")
        local_ids = get_ids(client, APP_BUCKET_NAME)
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
                    STATS["analyzed"].inc()
                    if item["id"] in local_ids:
                        STATS["skipped"].inc()
                        logging.info(
                            f"skipping already stored {item['id']} - {item['filename']}"
                        )
                        continue
                    if item["mediaMetadata"].get("photo"):  # PHOTO section
                        logging.info(f"analyzing {item['id']} - {item['filename']}")
                        # go to
                        # https://developers.google.com/photos/library/guides/access-media-items#base-urls
                        # for baseUrl handling
                        # works only for photos
                        base_url = f"{item['baseUrl']}=w{item['mediaMetadata']['width']}-h{item['mediaMetadata']['height']}-d"
                        with open(APP_TMP_FILENAME, "wb") as outfile:
                            download_media(base_url, outfile)
                        with open(APP_TMP_FILENAME, "rb") as infile:
                            item["sha1Checksum"] = put_filestorage(fs, infile)
                        put_metadata(client, APP_BUCKET_NAME, item)
                        STATS["copied"].inc()
                    elif item["mediaMetadata"].get("video"):  # VIDEO section
                        logging.info(f"analyzing {item['id']} - {item['filename']}")
                        # go to
                        # https://developers.google.com/photos/library/guides/access-media-items#base-urls
                        # for baseUrl handling
                        # works only for videos
                        base_url = f"{item['baseUrl']}=dv"
                        with open(APP_TMP_FILENAME, "wb") as outfile:
                            download_media(base_url, outfile)
                        with open(APP_TMP_FILENAME, "rb") as infile:
                            item["sha1Checksum"] = put_filestorage(fs, infile)
                        put_metadata(client, APP_BUCKET_NAME, item)
                        STATS["copied"].inc()
                    else:
                        STATS["skipped"].inc()
                        logging.info(
                            f"skipping non photo nor video {item['id']} - {item['filename']}"
                        )
                        logging.debug(json.dumps(item, indent=4))
                        continue
                except Exception as exc:
                    logging.exception(exc)
                    logging.debug(json.dumps(item, indent=4))
                    STATS["error"].inc()
                    raise exc
            logging.debug("Getting next page")
            results = (
                service.mediaItems()
                .list(pageToken=results.get("nextPageToken"))
                .execute()
            )
            items = results.get("mediaItems", [])
    logging.debug(json.dumps(stats, indent=4))


if __name__ == "__main__":
    # Start up the server to expose the metrics.
    start_http_server(9100)  # thats hard coded
    while True:
        try:
            starttime = time.time()
            main()
            duration = time.time() - starttime
            logging.info(f"sync took {duration} seconds to finish")
            time_left = max(
                0, APP_INTERVAL - duration
            )  # amount of seconds to sleep, at least zero
            logging.info(f"sleeping {time_left} seconds before doing the next loop")
            time.sleep(time_left)
        except Exception as exc:
            logging.exception(exc)
            logging.info(f"sleeping {APP_INTERVAL} seconds before doing the next loop")
            time.sleep(APP_INTERVAL)
