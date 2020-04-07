#!/usr/bin/env python3

import json
import sys
import os
import pika
import ujson
import logging
import psycopg2
import sys, traceback
import listenbrainz.utils as utils

from time import time, sleep
from listenbrainz.webserver import create_app
from flask import current_app
from listenbrainz.listenstore import TimescaleListenStore
from listenbrainz.listenstore import RedisListenStore
from listenbrainz.listen import Listen
from listenbrainz.listen_writer import ListenWriter
from psycopg2.errors import OperationalError, DuplicateTable, UntranslatableCharacter
from psycopg2.extras import execute_values
from listenbrainz.webserver import create_app
from flask import current_app
from requests.exceptions import ConnectionError
from redis import Redis
from collections import defaultdict
from listenbrainz import config

from listenbrainz.listen_writer import ListenWriter


TIMESCALE_QUEUE = "ts_incoming"

class TimescaleWriterSubscriber(ListenWriter):

    def __init__(self):
        super().__init__()

        self.ls = None
        self.timescale = None
        self.incoming_ch = None
        self.unique_ch = None
        self.redis_listenstore = None


    def callback(self, ch, method, properties, body):
        listens = ujson.loads(body)
        ret = self.write(listens)
        if not ret:
            return ret

        while True:
            try:
                self.incoming_ch.basic_ack(delivery_tag = method.delivery_tag)
                break
            except pika.exceptions.ConnectionClosed:
                self.connect_to_rabbitmq()

        count = len(listens)

        return ret

    def insert_to_listenstore(self, data, retries=5):
        """
        Inserts a batch of listens to the ListenStore. If this fails, then breaks the data into
        two parts and recursively tries to insert them, until we find the culprit listen

        Args:
            data: the data to be inserted into the ListenStore
            retries: the number of retries to make before deciding that we've failed

        Returns: number of listens successfully sent
        """

        if not data:
            return 0

        failure_count = 0
        while True:
            try:
                self.ls.insert(data)
                return len(data)
            except psycopg2.OperationalError as e:
                failure_count += 1
                if failure_count >= retries:
                    break
                sleep(self.ERROR_RETRY_DELAY)
            except ConnectionError as e:
                current_app.logger.error("Cannot write data to listenstore: %s. Sleep." % str(e), exc_info=True)
                sleep(self.ERROR_RETRY_DELAY)

        # if we get here, we failed on trying to write the data
        if len(data) == 1:
            # try to send the bad listen one more time and if it doesn't work
            # log the error
            try:
                self.ls.insert(data)
                return 1
            except (psycopg2.OperationalError, ValueError, ConnectionError) as e:
                error_message = 'Unable to insert bad listen to listenstore: {error}, listen={json}'
                timescale_dict = data[0]
                current_app.logger.error(error_message.format(error=str(e), json=json.dumps(timescale_dict, indent=3)), exc_info=True)
                return 0
        else:
            slice_index = len(data) // 2
            # send first half
            sent = self.insert_to_listenstore(data[:slice_index], retries)
            # send second half
            sent += self.insert_to_listenstore(data[slice_index:], retries)
            return sent

    def write(self, listens):
        '''
            This is quick and dirty for a proof of concept. Errors are logged, but data ruthlessly discarded.
        '''

        if not listens:
            return 0

        to_insert = []
        for listen in listens:
            tm = listen['track_metadata']
            # Clean up null characters in the data
            if 'artist_name' in tm and tm['artist_name']:
                tm['artist_name'] = tm['artist_name'].replace("\u0000", "")
            if 'track_name' in tm and tm['track_name']:
                 tm['track_name'] = tm['track_name'].replace("\u0000", "")
            if 'release_name' in tm and tm['release_name']:
                tm['release_name'] = tm['release_name'].replace("\u0000", "")

            to_insert.append([
                    listen['listened_at'],
                    listen['recording_msid'],
                    listen['user_name'],
                    ujson.dumps(tm)])

        with self.conn.cursor() as curs:
            # TODO: Later add this line to the query and pass the results down to the unique rmq
            query = """INSERT INTO listen 
                            VALUES %s
                       ON CONFLICT (listened_at, recording_msid, user_name)
                        DO NOTHING
                         RETURNING listened_at, recording_msid, user_name, data
                    """
            try:
                execute_values(curs, query, to_insert, template=None)
                result = curs.fetchone()
                self.conn.commit()
            except psycopg2.OperationalError as err:
                print("Cannot write data to timescale: %s." % str(err))
                return 0
            except Exception as err:
                print("Cannot write data to timescale: %s. Sleep." % str(err))
                traceback.print_exc()
                return 0

        return len(to_insert)


    def start(self):
        app = create_app()
        with app.app_context():
            print("timescale-writer init")
            self._verify_hosts_in_config()

            while True:
                try:
                    self.ls = TimescaleListenStore({ 'REDIS_HOST': config.REDIS_HOST,
                         'REDIS_PORT': config.REDIS_PORT,
                         'REDIS_NAMESPACE': config.REDIS_NAMESPACE,
                         'SQLALCHEMY_TIMESCALE_URI': config.SQLALCHEMY_TIMESCALE_URI
                    }, logger=current_app.logger)
                    break
                except Exception as err:
                    current_app.logger.error("Cannot connect to timescale: %s. Retrying in 2 seconds and trying again." % str(err), exc_info=True)
                    sleep(self.ERROR_RETRY_DELAY)

            while True:
                try:
                    self.redis = Redis(host=current_app.config['REDIS_HOST'], port=current_app.config['REDIS_PORT'], decode_responses=True)
                    self.redis.ping()
                    self.redis_listenstore = RedisListenStore(current_app.logger, current_app.config)
                    break
                except Exception as err:
                    current_app.logger.error("Cannot connect to redis: %s. Retrying in 2 seconds and trying again." % str(err), exc_info=True)
                    sleep(self.ERROR_RETRY_DELAY)

            while True:
                self.connect_to_rabbitmq()
                self.incoming_ch = self.connection.channel()
                self.incoming_ch.exchange_declare(exchange=current_app.config['INCOMING_EXCHANGE'], exchange_type='fanout')
                self.incoming_ch.queue_declare(current_app.config['INCOMING_QUEUE'], durable=True)
                self.incoming_ch.queue_bind(exchange=current_app.config['INCOMING_EXCHANGE'], queue=TIMESCALE_QUEUE)
                self.incoming_ch.basic_consume(
                    lambda ch, method, properties, body: self.static_callback(ch, method, properties, body, obj=self),
                    queue=TIMESCALE_QUEUE,
                )

                self.unique_ch = self.connection.channel()
                self.unique_ch.exchange_declare(exchange=current_app.config['UNIQUE_EXCHANGE'], exchange_type='fanout')

                current_app.logger.info("timescale-writer started")
                try:
                    self.incoming_ch.start_consuming()
                except pika.exceptions.ConnectionClosed:
                    current_app.logger.warn("Connection to rabbitmq closed. Re-opening.", exc_info=True)
                    self.connection = None
                    continue

                self.connection.close()
            except Exception as err:
                traceback.print_exc()
                print("failed to start timescale loop ", str(err))


if __name__ == "__main__":
    rc = TimescaleWriterSubscriber()
    rc.start()
