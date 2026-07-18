"""Private storage aliases shared by Library uploads and generated exports."""

from django.core.files.storage import storages


def private_upload_storage():
    return storages["private"]


def private_export_storage():
    return storages["exports"]
