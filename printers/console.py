#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

class bcolors:
	HEADER = '\033[1m\033[95m'
	OKBLUE = '\033[94m'
	OKGREEN = '\033[92m'
	WARNING = '\033[93m'
	FAIL = '\033[1m\033[91m'
	ENDC = '\033[0m'

class ConsoleManager(object):

	def __init__(self):
		pass

	def print_title(self, tt):
		print bcolors.HEADER + tt + bcolors.ENDC

	def print_list(self, lst):
		for s in lst:
			print bcolors.OKGREEN + "\t · " + str(s) + bcolors.ENDC

	def print_dict(self, dct):
		for mth in dct:
			print bcolors.OKGREEN + "\t - " + mth + bcolors.ENDC
			for str_m in dct[mth]:
				print bcolors.OKBLUE + "\t\t - " + str_m + bcolors.ENDC

	def print_error(self, msg):
		print bcolors.FAIL + msg + bcolors.ENDC