# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import uuid
import unittest


class ParserTestCase(unittest.TestCase):

    def call_target(self, *args, **kwargs):
        from ..utils import app_parser
        return app_parser(*args, **kwargs)

    def test_positional_arguments(self):
        parser = self.call_target()
        args = parser.parse_args(['testing.ini'])
        self.assertEqual(args.config_uri, 'testing.ini')
        self.assertFalse(args.with_example_data)
        self.assertIsNone(args.superuser)
        self.assertIsNone(args.super_password)
        self.assertEqual(args.config_name, 'main')

    def test_optional_arguments(self):
        parser = self.call_target()
        args = parser.parse_args(['testing.ini',
                                  '--with-example-data',
                                  '--superuser', 'superman',
                                  '--super-password', 'clarkkent',
                                  '--config-name', 'NEW_NAME'])
        self.assertEqual(args.config_uri, 'testing.ini')
        self.assertTrue(args.with_example_data)
        self.assertEqual(args.superuser, 'superman')
        self.assertEqual(args.super_password, 'clarkkent')
        self.assertEqual(args.config_name, 'NEW_NAME')

    def test_help(self):
        import subprocess
        parser = self.call_target(
            description='Commandline script '
                        'used to initialize the SQL database.')
        expected_help_message = parser.format_help()
        actual_help_message = subprocess.check_output(
            ["cnx-archive-initdb", "--help"])
        expected_help_message = expected_help_message.split()
        actual_help_message = actual_help_message.split()
        self.assertEqual(expected_help_message, actual_help_message)


class SettingsTestCase(unittest.TestCase):

    def call_target(self, *args, **kwargs):
        from ..utils import app_settings
        from ..utils import app_parser
        parser = app_parser()
        arguments = parser.parse_args(*args, **kwargs)
        return app_settings(arguments)

    def test_default_config(self):
        from testing import integration_test_settings
        import os
        expected = integration_test_settings()
        here = os.path.abspath(os.path.dirname(__file__))
        config_uri = os.path.join(here, 'testing.ini')
        result = self.call_target([config_uri])
        self.assertEqual(expected, result)

    def test_example_arg(self):
        import os
        settings = self.call_target(['cnxarchive/tests/testing.ini'])
        self.assertFalse(settings['with_example_data'])
        settings = self.call_target(
            ['cnxarchive/tests/testing.ini', '--with-example-data'])
        self.assertTrue(settings['with_example_data'])

    def test_superuser_arg(self):
        settings = self.call_target(
            ['cnxarchive/tests/testing.ini', '--superuser', 'superman'])
        self.assertEqual(settings['superuser'], 'superman')

    def test_password_arg(self):
        settings = self.call_target(
            ['cnxarchive/tests/testing.ini', '--super-password', 'clarkkent'])
        self.assertEqual(settings['super_password'], 'clarkkent')

    def test_default_config_name(self):
        settings = self.call_target(['cnxarchive/tests/testing.ini'])
        self.assertEqual(settings['config_name'], 'main')

class SplitIdentTestCase(unittest.TestCase):

    def call_target(self, *args, **kwargs):
        from cnxdb.ident_hash import split_ident_hash
        return split_ident_hash(*args, **kwargs)

    def test_empty_value(self):
        # Case of supplying the utility function with an empty indent-hash.
        ident_hash = ''

        with self.assertRaises(ValueError):
            self.call_target(ident_hash)

    def test_complete_data(self):
        # Simple case of supplying the correct information and checking
        # for the correct results.
        expected_id, expected_version = (
            '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2', '1.12',
        )
        ident_hash = "{}@{}".format(expected_id, expected_version)

        id, version = self.call_target(ident_hash)

        self.assertEqual(id, expected_id)
        self.assertEqual(version, expected_version)

    def test_uuid_only(self):
        # Case where the UUID has been the only value supplied in the
        # ident-hash.
        # This is mostly testing that the version value returns None.
        expected_id, expected_version = (
            '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2', '',
            )
        ident_hash = "{}@{}".format(expected_id, expected_version)

        id, version = self.call_target(ident_hash)

        self.assertEqual(id, expected_id)
        self.assertEqual(version, None)

    def test_invalid_id(self):
        # Case for testing for an invalid identifier.
        ident_hash = "not-a-valid-id@"

        from cnxdb.ident_hash import IdentHashSyntaxError
        with self.assertRaises(IdentHashSyntaxError):
            self.call_target(ident_hash)

    def test_invalid_syntax(self):
        # Case for testing the ident-hash's syntax guards.
        ident_hash = "85e57f7902b347d28eedc1bbb1e1d5c2@1.2@select*frommodules"

        from cnxdb.ident_hash import IdentHashSyntaxError
        with self.assertRaises(IdentHashSyntaxError):
            self.call_target(ident_hash)

    def test_w_split_version(self):
        expected_id, expected_version = (
            '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2',
            ('1', '12',),
            )
        ident_hash = "{}@{}".format(expected_id, '.'.join(expected_version))

        id, version = self.call_target(ident_hash, True)

        self.assertEqual(id, expected_id)
        self.assertEqual(version, expected_version)

    def test_w_split_version_on_major_version(self):
        expected_id, expected_version = (
            '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2',
            ('1', None,),
            )
        ident_hash = "{}@{}".format(expected_id, expected_version[0])

        id, version = self.call_target(ident_hash, True)

        self.assertEqual(id, expected_id)
        self.assertEqual(version, expected_version)

    def test_w_split_version_no_version(self):
        expected_id, expected_version = (
            '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2',
            (None, None,)
            )
        ident_hash = expected_id

        id, version = self.call_target(ident_hash, True)

        self.assertEqual(id, expected_id)
        self.assertEqual(version, expected_version)


class JoinIdentTestCase(unittest.TestCase):

    def call_target(self, *args, **kwargs):
        from cnxdb.ident_hash import join_ident_hash
        return join_ident_hash(*args, **kwargs)

    def test(self):
        id = '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2'
        version = ('2', '4',)
        expected = "{}@{}".format(id, '.'.join(version))
        ident_hash = self.call_target(id, version)
        self.assertEqual(expected, ident_hash)

    def test_w_UUID(self):
        id = uuid.uuid4()
        version = None
        expected = str(id)
        ident_hash = self.call_target(id, version)
        self.assertEqual(expected, ident_hash)

    def test_w_null_version(self):
        id = '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2'
        version = None
        expected = id
        ident_hash = self.call_target(id, version)
        self.assertEqual(expected, ident_hash)

    def test_w_null_str_version(self):
        id = '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2'
        version = ''
        expected = id
        ident_hash = self.call_target(id, version)
        self.assertEqual(expected, ident_hash)

    def test_w_str_version(self):
        id = '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2'
        version = '2'
        expected = "{}@{}".format(id, version)
        ident_hash = self.call_target(id, version)
        self.assertEqual(expected, ident_hash)

    def test_w_major_version(self):
        id = '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2'
        version = ('2', None,)
        expected = "{}@{}".format(id, version[0])
        ident_hash = self.call_target(id, version)
        self.assertEqual(expected, ident_hash)


    def test_w_double_null_version(self):
        id = '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2'
        version = (None, None,)
        expected = id
        ident_hash = self.call_target(id, version)
        self.assertEqual(expected, ident_hash)

    def test_w_invalid_version_sequence(self):
        id = '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2'
        version = ('1',)
        with self.assertRaises(AssertionError):
            self.call_target(id, version)

    def test_w_integer_version(self):
        id = '85e57f79-02b3-47d2-8eed-c1bbb1e1d5c2'
        version = (1, 2,)
        expected = '{}@1.2'.format(id)
        ident_hash = self.call_target(id, version)
        self.assertEqual(expected, ident_hash)
