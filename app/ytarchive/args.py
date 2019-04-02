#!/usr/bin/env python3
from argparse import ArgumentParser


def get_args():
	parser = ArgumentParser()
	parser.add_argument("-s", "--site", help="limit operations to the provided site id", type=int)
	args = parser.parse_args()
	return args
