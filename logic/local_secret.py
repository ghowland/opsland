"""
Simple library to load a local secret from a file, does user dir expansion
"""


import os


def Get(path_raw):
	path = os.path.expanduser(path_raw)

	with open(path) as fp:
		return fp.read().strip()
