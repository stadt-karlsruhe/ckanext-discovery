# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound

from ckan.model.meta import Session


log = logging.getLogger(__name__)


class Object(object):
    '''
    Base class for ORM classes.

    To create a declarative base for SQLAlchemy using this class::

        Base = declarative_base(cls=Object)

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
        return cls.query().filter_by(**kwargs).one()

    @classmethod
    def filter_by(cls, **kwargs):
        return cls.query().filter_by(**kwargs)

    @classmethod
    def filter(cls, *args, **kwargs):
        return cls.query().filter(*args, **kwargs)

    @classmethod
    def query(cls):
        return Session.query(cls)

