import sqlalchemy

from datetime import datetime, timedelta
from listenbrainz import db
from listenbrainz.db.model.cover_art import CoverArt
from typing import List

TIME_TO_CONSIDER_COVER_ART_STALE = 7  # days


def insert(cover_art: CoverArt):
    """ Inserts a cover_art record for a given release into the database.
        If the record is already present for the release MBID, the image_url is updated to the new
        value passed.

        Args:
            cover_art: An object of class CoverArt
    """

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO cover_art (release_mbid, image_url, source)
                 VALUES (:release_mbid, :image_url, :score)
            ON CONFLICT (user_id, source)
          DO UPDATE SET image_url = :image_url,
                        created = NOW()
            """), {
            'release_mbid': cover_art.release_mbid,
            'image_url': cover_art.image_url,
            'source': cover_art.source,
        }
        )


def get_cover_art_for_release(release_mbid: int, source: int = None) -> List[CoverArt]:
    """ Get a list of cover_art given for a release in descending order of their creation

        Args:
            release_mbid: the MusicBrainz ID of the release
            source: the source from where the cvoer art image was taken.

        Returns:
            A list of CoverArt objects
    """

    max_validity_time = datetime.now() + timedelta(days=TIME_TO_CONSIDER_COVER_ART_STALE)

    args = {"release_mbid": release_mbid, "max_validity_time": max_validity_time}
    query = """ SELECT release_mbid,
                       image_url,
                       source,
                       created
                  FROM cover_art
                 WHERE release_mbid = :release_mbid
                   AND created <= :max_validity_time """

    if source:
        query += " AND source = :source "
        args["source"] = source

    query += " ORDER BY created DESC "

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text(query), args)
        return [CoverArt(**dict(row)) for row in result.fetchall()]
