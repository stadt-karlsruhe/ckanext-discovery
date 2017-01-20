# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging

from sqlalchemy import Column, types, ForeignKey
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

from ckan.model.meta import Session


log = logging.getLogger(__name__)

Base = declarative_base()


class Object(Base):
    '''
    Base class for ORM classes.
    '''
    __abstract__ = True

    # Based on http://stackoverflow.com/a/37419325/857390
    @classmethod
    def get_or_create(cls, create_kwargs=None, **kwargs):
        '''
        Get an instance or create it.

        At first all keyword arguments are used to search for a single
        instance. If that instance is found it is returned. If no
        instance is found then it is created using the keyword arguments
        and any additional arguments given in the ``create_kwargs``
        dict. The created instance is then returned.
        '''
        if not kwargs:
            raise ValueError('No filter keyword arguments.')
        try:
            # First assume that the object already exists
            return cls.one(**kwargs)
        except NoResultFound:
            # Since the object doesn't exist, try to create it
            kwargs.update(create_kwargs or {})
            obj = cls(**kwargs)
            try:
                with Session.begin_nested():
                    Session.add(obj)
                return obj
            except IntegrityError as e:
                log.exception(e)
                # Assume someone has raced the object creation
                return cls.one(**kwargs)

    @classmethod
    def one(cls, **kwargs):
        return Session.query(cls).filter_by(**kwargs).one()

    @classmethod
    def filter_by(cls, **kwargs):
        return Session.query(cls).filter_by(**kwargs)

    @classmethod
    def filter(cls, *args, **kwargs):
        return Session.query(cls).filter(*args, **kwargs)


class SearchTerm(Object):
    '''
    A single search term.
    '''
    __tablename__ = 'discovery_searchterm'
    id = Column(types.Integer, primary_key=True, nullable=False)
    term = Column(types.UnicodeText, unique=True, nullable=False, index=True)
    count = Column(types.Integer, default=0, nullable=False)

    def __repr__(self):
        r = '<{} "{}">'.format(self.__class__.__name__, self.term)
        return r.encode('utf-8')


class CoOccurrence(Object):
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
    Base.metadata.create_all(engine)

