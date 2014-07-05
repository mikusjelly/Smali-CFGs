#!/usr/bin/env python
# -*- coding: utf-8 -*-

from walkers.base	import Walker
from walkers.strings import StringsFinder
from walkers.packages import PackagesFinder
from walkers.calls import CallsFinder
from walkers.instructions import InstructionsFinder

from printers.graphs import GraphManager
from printers.console import ConsoleManager

from libs.cmd2 import Cmd, make_option, options
import optparse, sys

#import getopt, sys

class CmdLineApp(Cmd):
	Cmd.shortcuts.update({'!pu': 'packageUsage'})
	Cmd.shortcuts.update({'!sp': 'stringpatternmatch'})
	Cmd.shortcuts.update({'!if': 'instructionflow'})
	Cmd.shortcuts.update({'!xf': 'crossreferences'})
	walker = None

	def init(self, where):
		self.walker = Walker(where)
		self.cprint = ConsoleManager()

	@options([
		make_option('-m', '--matchs_inmethod', action="store", help="Show details about matches in specified method.", default=False, metavar="<METHOD>")
	])
	def do_stringpatternmatch(self, arg, opts=None):
		if (not arg):
			self.cprint.print_error("Incorrect Syntax: help stringpatternmatch.\n")
		else:
			strings_patterns = sorted(list(set(arg.split(' '))))
			if len(strings_patterns[0]) == 0: strings_patterns = strings_patterns[1:]

			fnd = StringsFinder(strings_patterns)
			self.walker.assign_finder(fnd)
			results = self.walker.do_find()
			if len(results)>0:
				if opts.matchs_inmethod:
					method_definition = repr(opts.matchs_inmethod)[2:-2]
					if results[method_definition]:
						self.cprint.print_title("· String Patterns %s matches at %s are:" % (strings_patterns, method_definition))
						self.cprint.print_list(results[method_definition])
				else:
					self.cprint.print_title("· String Patterns %s have been located at above Application Methods:" % (strings_patterns))
					self.cprint.print_list(results)

	def do_packageusage(self, arg, opts=None):
		if (not arg):
			self.cprint.print_error("Incorrect Syntax: help packageusage.\n")
		else:
			arg = ''.join(arg)
			fnd = PackagesFinder(arg)
			self.walker.assign_finder(fnd)
			pkgData = self.walker.do_find()
			if len(pkgData)>0:
				self.cprint.print_title("*  Analized Application uses the next %s Methods:" % arg)
				self.cprint.print_list(sorted(pkgData))

	@options([
		make_option('-f', '--full_graph', action="store_true", help="Include outmethod calls in flow.", default=False, metavar="<BOOL>"),
		make_option('--store_dot', action="store_true", default=False, help="Optional")
	])
	def do_instructionflow(self, arg, opts=None):
		if (not arg):
			self.cprint.print_error("Incorrect Syntax: help instructionflow.\n")
		else:
			method_definition = repr(''.join(arg))[2:-2]
			self.cprint.print_title("*  Method %s Instructions Flow saved to MethodInstructionsFlow.png." % (method_definition))
			fnd = InstructionsFinder(method_definition, opts.full_graph)
			self.walker.assign_finder(fnd)
			resultados = self.walker.do_find()
			graph_mgr = GraphManager(True)
			for b1 in resultados:
				for lbl,target in b1.bifurcaciones:
					for b2 in resultados:
						if b2.etiqueta == target:
							graph_mgr.add_block_edge(b1,b2, lbl)
							break

			try:
				graph_mgr.draw("MethodInstructionsFlow", not opts.store_dot)
			except:
				self.cprint.print_error("Complex Graph can't be rendered with graphviz libraries, using .dot format instead!\n")
				graph_mgr.draw("MethodInstructionsFlow", False)

	@options([
		make_option('--str_reg', action="store", help="Optional", metavar="[<REG>"),
		make_option('--max_levels', action="store", type="int", default=1, help="Optional", metavar="<LEVEL>"),
		make_option('--direction', action="store", type="int", default=2, help="Optional", metavar="<NUM> (0=to, 1=from, 2=both)"),
		make_option('--view_system_calls', action="store_true", default=False, help="Optional"),
		make_option('--store_dot', action="store_true", default=False, help="Optional")
	])
	def do_crossreferences(self, arg, opts=None):
		def cross_level(start_points, direction, view_system_calls, lvl):
			auxCalls = []
			for methodPair in start_points:
				fcaller, fcalled = methodPair

				fnd = CallsFinder(fcaller)
				self.walker.assign_finder(fnd)
				mthXrefs = self.walker.do_find()

				for callPair in mthXrefs:
					caller, called = callPair
					if direction == 0:
						condition = (called == fcaller)
					elif direction == 1:
						condition = (caller == fcaller)
					else:
						condition = True

					if condition:
						if (caller, called) not in auxCalls:
							if view_system_calls:
								auxCalls.append( (caller, called) )
							else:
								if lvl==0:
									auxCalls.append( (caller, called) )
								else:
									if called.split('->')[0] in self.walker.AppInventory.keys():
										auxCalls.append( (caller, called) )
			return auxCalls

		if (not arg):
			self.cprint.print_error("Incorrect Syntax: help crossreferences.\n")
			return

		# arg
		method_definition = repr(''.join(arg))[2:-2]

		# str patterns
		StringMatch = None
		if opts.str_reg:
			strings_patterns = [opts.str_reg]
			fnd = StringsFinder(strings_patterns)
			self.walker.assign_finder(fnd)
			StringMatch = self.walker.do_find()

		if StringMatch:
			self.cprint.print_title("*  Cross-References with a %d recursion level and String Pattern search." % (opts.max_levels))
		else:
			self.cprint.print_title("*  Cross-References with a %d recursion level." % (opts.max_levels))

		level = 0
		PackageUsage = []
		results = []
		PackageUsage.append( (method_definition,'') )
		while True:
			PackageUsage2 = cross_level(PackageUsage, opts.direction, opts.view_system_calls, level)
			if len(PackageUsage) == len(PackageUsage2):
				equal = True
				for a in PackageUsage:
					equal = a in PackageUsage2
					if not equal: break
				if equal: break
			results += PackageUsage2
			PackageUsage = PackageUsage2
			level +=1
			if level == opts.max_levels: break

		graph_mgr = GraphManager()
		coincidences = {}

		for calls in results:
			caller, called = calls
			graph_mgr.add_xref_edge(caller, called, method_definition, StringMatch)
			if StringMatch:
				if (caller in StringMatch) and (caller not in coincidences):
					coincidences[caller] = StringMatch[caller]
				elif (called in StringMatch) and (called not in coincidences):
					coincidences[called] = StringMatch[called]

		self.cprint.print_dict(coincidences)

		if StringMatch:
			try:
				graph_mgr.draw("CrossReferencesWithPatterns", not opts.store_dot)
			except:
				self.cprint.print_error("Complex Graph can't be rendered with graphviz libraries, using .dot format instead!\n")
				graph_mgr.draw("CrossReferencesWithPatterns", False)
		else:
			try:
				graph_mgr.draw("CrossReferences", not opts.store_dot)
			except:
				self.cprint.print_error("Complex Graph can't be rendered with graphviz libraries, using .dot format instead!\n")
				graph_mgr.draw("CrossReferences", False)


app = CmdLineApp()
app.cmdloop()