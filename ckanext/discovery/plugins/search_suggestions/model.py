# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging

from sqlalchemy import Column, DDL, event, ForeignKey, Index, types
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.sql import func

from ...model import Object


log = logging.getLogger(__name__)

Base = declarative_base(cls=Object)


class SearchTerm(Base):
    '''
    A single search term.
    '''
    __tablename__ = 'discovery_searchterm'
    id = Column(types.Integer, primary_key=True, nullable=False)
    term = Column(types.UnicodeText, unique=True, nullable=False, index=True)
    count = Column(types.Integer, default=0, nullable=False)
    term_tsvector = Column(TSVECTOR)
    __table__args = (
        Index('discovery_searchterm_term_tsvector_idx', 'term_tsvector',
              postgresql_using='gin'),
    )

    def __repr__(self):
        r = '<{} "{}">'.format(self.__class__.__name__, self.term)
        return r.encode('utf-8')

    @classmethod
    def by_prefix(cls, prefix):
        '''
        Find search terms with a given prefix.
        '''
        # In our SQLAlchemy version the language cannot be specified in the
        # `match` function, so we construct the query explicitly. See
        # https://bitbucket.org/zzzeek/sqlalchemy/issues/3078
        tsquery = func.to_tsquery('pg_catalog.simple', "'{}':*".format(prefix))
        return cls.filter(
            cls.term_tsvector.op('@@')(tsquery)
        )


# Register a trigger that automatically updates the `term_tsvector` column
# when a SearchTerm is added or changed.
_term_tsvector_trigger = DDL('''
    CREATE TRIGGER discovery_search_term_tsvector_update
    BEFORE INSERT OR UPDATE ON {table}
    FOR EACH ROW EXECUTE PROCEDURE
    tsvector_update_trigger(term_tsvector, 'pg_catalog.simple', term)
'''.format(table=SearchTerm.__tablename__))
event.listen(SearchTerm.__table__, 'after_create',
             _term_tsvector_trigger.execute_if(dialect='postgresql'))


class CoOccurrence(Base):
    '''
    Co-occurrences of two search terms.

    The corresponding table represents a co-occurrence matrix. Since
    the matrix is symmetrical, only one half of it has to be stored.
    This is achieved by sorting the two terms of a ``CoOccurrence`` so
    that the first term is lexicographically smaller than the second.
    '''
    __tablename__ = 'discovery_cooccurrence'
    term1_id = Column(types.Integer, ForeignKey(SearchTerm.id,
                      ondelete='CASCADE', onupdate='CASCADE'),
                      nullable=False, primary_key=True)
    term1 = relationship(SearchTerm, foreign_keys=term1_id)
    term2_id = Column(types.Integer, ForeignKey(SearchTerm.id,
                      ondelete='CASCADE', onupdate='CASCADE'),
                      nullable=False, primary_key=True)
    term2 = relationship(SearchTerm, foreign_keys=term2_id)
    count = Column(types.Integer, default=0, nullable=False)

    @property
    def similarity(self):
        '''
        The similarity of the two terms.

        Returns a float between 0 (no similarity) and 1 (terms only
        occur in combination).
        '''
        return self.count / (self.term1.count + self.term2.count - self.count)

    @classmethod
    def for_term(cls, term):
        '''
        Query all co-occurrences of a ``SearchTerm``.
        '''
        return cls.filter((cls.term1 == term) | (cls.term2 == term))

    @classmethod
    def for_words(cls, word1, word2):
        '''
        The co-occurrence for two words.
        '''
        word1, word2 = sorted([word1, word2])
        term1 = SearchTerm.get_or_create(term=word1)
        term2 = SearchTerm.get_or_create(term=word2)
        return cls.get_or_create(term1=term1, term2=term2)

    def __repr__(self):
        r = '<{} "{}", "{}">'.format(self.__class__.__name__,
                                     self.term1.term,
                                     self.term2.term)
        return r.encode('utf-8')


def create_tables():
    '''
    Create the necessary database tables.
    '''
    log.debug('Creating database tables')
    from ckan.model.meta import engine
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

