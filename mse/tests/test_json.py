# -*- coding: utf-8 -*-
"""Unit test cases for testing the JSONification of data model objects."""

from turbogears.database import session
from turbogears import testutil

from mse.model import Group, Permission, User
from mse.jsonify import jsonify


class JsonifyTest(testutil.DBTest):
    """Unit tests for JSONification of the identity model objects."""

    def setUp(self):
        super(JsonifyTest, self).setUp()
        self.test_user = u = User(
            user_name = u'test',
            display_name = u'Test User',
            email_address = u'test@nowhere.tld',
            password = u'test')
        self.test_group = g = Group(
            group_name = u'test',
            display_name = u'Test Group')
        u.addGroup(g)
        self.test_perm = p = Permission(
            permission_name = u'test',
            description = u'Test Permission')
        p.addGroup(g)

    def test_jsonify_group(self):
        """Test that Group model objects are correctly jsonified."""
        json = jsonify(self.test_group)
        assert json['group_name'] == u'test'
        assert json['display_name'] == u'Test Group'
        assert json['users'] == [u'test']
        assert json['permissions'] == [u'test']

    def test_jsonify_permission(self):
        """Test that Permission model objects are correctly jsonified."""
        json = jsonify(self.test_perm)
        assert json['permission_name'] == u'test'
        assert json['description'] == u'Test Permission'
        assert json['groups'] == [u'test']

    def test_jsonify_user(self):
        """Test that User model objects are correctly jsonified."""
        json = jsonify(self.test_user)
        assert json['user_name'] == u'test'
        assert json['display_name'] == u'Test User'
        assert json['email_address'] == u'test@nowhere.tld'
        assert 'password' not in json
        assert '_password' not in json
        assert json['groups'] == [u'test']
        assert json['permissions'] == [u'test']
