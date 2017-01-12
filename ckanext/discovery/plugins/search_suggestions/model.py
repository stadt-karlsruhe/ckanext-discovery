# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging

from sqlalchemy import Column, types, text
from sqlalchemy.ext.declarative import declarative_base

from ckan.model.meta import engine, Session

from . import get_language


log = logging.getLogger(__name__)

Base = declarative_base()


def _execute(sql, **kwargs):
    '''
    Execute a raw SQL string.

    Keyword arguments can be used to provide values for placeholders::

        _execute('SELECT foo FROM bar WHERE x > :value;', value=20)

    Returns a ``ResultProxy``.
    '''
    with engine.connect() as conn:
        return conn.execute(text(sql), **kwargs)


class SearchQuery(Base):
    '''
    A search query.
    '''
    __tablename__ = 'discovery_searchquery'

    id = Column(types.Integer, primary_key=True)

    # The search string. Named after the Solr parameter of the same name, from
    # which the values are taken.
    q = Column(types.UnicodeText, nullable=False)

    @classmethod
    def suggest(cls, terms, limit=10, min_score=0):
        '''
        Suggest search queries.

        ``terms`` is a list of search terms.

        ``limit`` is the maximum number of suggestions returned.

        Suggestions with a score below ``min_score`` are not listed.

        The return value is a list of suggested search queries, sorted
        descendingly by their similarity to the given terms.
        '''
        # The following query first finds the rows that contain at least one of
        # the terms. These rows are then sorted by score/rank, which is done in
        # a separate query to avoid rank computations for all those rows that
        # don't contain a term. Finally, rows with a score less than
        # `min_score` are dropped. This is again done in a separate query to
        # avoid the repetition of the call to `ts_rank`, see
        # http://stackoverflow.com/a/12866110/857390).
        results = _execute(
            '''
            SELECT *
            FROM (
                SELECT
                    match.id AS id,
                    ts_rank(to_tsvector(:language, match.q),
                            to_tsquery(:language, :terms)) AS rank
                FROM (
                    SELECT id, q
                    FROM {table}
                    WHERE to_tsvector(:language, q) @@ to_tsquery(:language, :terms)
                ) AS match
                ORDER BY rank DESC
            ) AS sorted
            WHERE rank >= :min_rank
            LIMIT :limit;
            '''.format(table=cls.__tablename__),
            language=get_language(),
            terms = ' | '.join(terms),
            limit=limit,
            min_rank=min_score,
        )
        ids = [r[0] for r in results]
        queries = {q.id: q
                   for q in Session.query(cls).filter(cls.id.in_(ids)).all()}
        return ids, [queries[id] for id in ids]


def create_tables():
    '''
    Create the necessary database tables.
    '''
    log.debug('Creating database tables')
    Base.metadata.create_all(engine)

    # Create a text-search index to speed up text searches. See
    # https://www.postgresql.org/docs/current/static/textsearch-tables.html
    log.debug('Creating text search index')
    table = SearchQuery.__tablename__
    _execute(
        '''
        DROP INDEX IF EXISTS {index};
        CREATE INDEX {index} ON {table}
            USING GIN (to_tsvector(:language, q));
        '''.format(table=table, index=table + '_ts_index'),
        language=get_language(),
    )

