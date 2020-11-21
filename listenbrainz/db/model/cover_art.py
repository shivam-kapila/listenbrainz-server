import uuid

from datetime import datetime
from pydantic import BaseModel, ValidationError, validator


class CoverArt(BaseModel):
    """ Represents a cached cover art object
        Args:
            release_mbid: the MusicBrainz ID of the recording
            image_url: the URL for the cover art image
            source: the source from where the cover art was taken
            created: (Optional) the timestamp when the cover art record was inserted into DB
    """

    release_mbid: str
    image_url: str
    source: str
    created: datetime = None

    @validator("release_mbid")
    def check_recording_msid_is_valid_uuid(cls, release_mbid):
        try:
            release_mbid = uuid.UUID(release_mbid)
            return str(release_mbid)
        except (AttributeError, ValueError):
            raise ValueError("Release MBID must be a valid UUID.")
