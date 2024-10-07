#!/usr/bin/env python

'''
Test package integrity
'''

import unittest


class TestPackage(unittest.TestCase):

    def test_import(self):
        import runningman