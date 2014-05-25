import sys
import os
import re
from optparse import OptionParser

import pydot

class GraphManager(object):
	def __init__(self):
		self.graph = pydot.Dot(graph_type='digraph', simplify=True, rankdir="LR", fontsize=40, labelloc="t" )
		#self.graph.set_bgcolor('#000000')

	def add_edge(self, b1, b2, corder, main_method):
		nodes = []
		strs = [ b1, b2 ]
		for strn in strs:
			if strn == main_method:
				n = pydot.Node(strn, color="red", style="filled", shape="record", fontname="Sans", fontsize=8 )
			else:
				n = pydot.Node(strn, style="filled", shape="record", color="#cccccc", fontname="Sans", fontsize=8 )
			self.graph.add_node(n)
			nodes.append(n)
		self.graph.add_edge(pydot.Edge(nodes[0], nodes[1], color="#666666", arrowhead="open", label=corder, fontsize=8))

	def draw(self, name, single):
		self.graph.set_label(name)
		if single:
			self.graph.write_png(name + "_single.png")
		else:
			self.graph.write(name + "_full.dot")

class SmaliFilesManager(object):
	def __init__(self, dir, method, single=True):
		self.location = dir
		self.definition = method
		self.single = single
		self.method_inventory = []
		self.graph = GraphManager()

	def _getFileContent(self, definition):
		cfile = definition.split('->')[0].split('/')[-1][:-1]
		cdir  = "/".join(definition.split('->')[0].split('/')[:-1])[1:]
		cmet  = definition.split('->')[1]
		filename = self.location + "/" + cdir + "/" + cfile + ".smali"
		with open(filename, "r") as fh:
			fcontent = fh.read()
		return fcontent

	def _createInventory(self):
		for root, subFolders, files in os.walk(self.location):
			for file in files:
				if file.endswith(".smali"):
					with open(root+"/"+file, "r") as file_handle:
						smali_content = file_handle.read()
						class_search = re.search('\.class\s+(.*?)\n', smali_content)
						class_definition = class_search.group(0)[:-1].split(' ')[-1][:-1]
						method_definitions = re.findall('\.method\s+(.*?)\n', smali_content)
						for method in method_definitions:
							self.method_inventory.append("%s->%s" % (class_definition, method.split(' ')[-1][:-1]) )

	def searchCallCrossReferences(self):
		self._createInventory()
		calls_to_review = [self.definition]
		analized_calls = []
		nCalls = nMethods = 0
		while True:
			mname = calls_to_review[nMethods]
			fcontent = self._getFileContent(mname)
			class_definition = re.findall('\.class\s+(.*?)\n',fcontent)[0].split(' ')[-1][:-1]
			for m in re.findall('\.method\s+(.*?)\.end\s+method', fcontent, re.DOTALL):
				method_definition = "%s->%s" % (class_definition, m.split('\n')[0].split(' ')[-1][:-1])
				for c in re.findall("invoke-(.*?)\r", m):
					call_definition = c.split(' ')[-1]
					if mname + "," + call_definition not in analized_calls:
						if call_definition not in calls_to_review:
							if call_definition in self.method_inventory:
								calls_to_review.append( call_definition )
							if self.single:
								if call_definition in self.method_inventory:
									self.graph.add_edge(mname, call_definition, nCalls, self.definition)
									analized_calls.append( mname + "," + call_definition )
									nCalls += 1
							else:
								self.graph.add_edge(mname, call_definition, nCalls, self.definition)
								analized_calls.append( mname + "," + call_definition )
								nCalls += 1
			nMethods += 1
			if nMethods >= len(calls_to_review): break

	def writeGraphToFile(self, name):
		self.graph.draw(name, self.single)

if __name__ == '__main__':

	usage = "usage: %prog [options]"
	parser = OptionParser(usage=usage)
	parser.add_option("-d", "--directory", action="store", type="string", dest="smali_rootdir",
                  help="Smali code directory entry point.")
	parser.add_option("-m", "--method", action="store", type="string", dest="ref_method",
                  help="Full class method definition string to look for.")

	(options, args) = parser.parse_args()
	if (not options.smali_rootdir):
		parser.error("option -d is mandatory.")
	if (not options.ref_method):
		parser.error("Option -m is mandatory.")

	rootdir = options.smali_rootdir
	ref_method = options.ref_method
	fname = ref_method.split('->')[1].split('(')[0]
	smaliManager = SmaliFilesManager(rootdir, ref_method, single=True)
	smaliManager.searchCallCrossReferences()
	smaliManager.writeGraphToFile(fname)