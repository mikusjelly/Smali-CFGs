import sys
import os
import re
import pydot
import urllib
from optparse import OptionParser

# Class method/s execution flow (no outside class calls analized)
##
class GraphManager(object):
	""" pydot graph objects manager """
	def __init__(self):
		self.graph = pydot.Dot(graph_type='digraph', simplify=True)

	def add_edge(self, b1, b2, label="CONT"):
		""" join two pydot nodes / create nodes edge """
		# Edge color based on label text
		if label=='false':
			ecolor = "red"
		elif label=='true':
			ecolor = 'green'
		elif label == 'exception':
			ecolor = 'orange'
		elif label == 'try':
			ecolor = 'blue'
		else:
			ecolor = 'gray'

		# node shape based on block type (First or Last instruction)
		nodes = [None, None]
		blocks = [b1,b2]
		for i in range(2):
			if re.search("^if-", blocks[i].instructions[-1]) != None:
				ncolor = "cornflowerblue"
			elif re.search("^\:" , blocks[i].instructions[0]) != None:
				ncolor = "tan"
			elif re.search("^goto", blocks[i].instructions[-1]) != None:
				ncolor = "darkgreen"
			elif re.search("^invoke-", blocks[i].instructions[-1]) != None:
				ncolor = "lightyellow4"
			else:
				ncolor = "mediumaquamarine"

			insTxt = "%s\r" % blocks[i].label
			lidx = int(blocks[i].label.split(' ')[-1])
			for ii in blocks[i].instructions:
				insTxt += str(lidx) +  ": " + ii
				lidx+=1

			nodes[i] = pydot.Node(b1.label, color=ncolor, style="filled", shape="box", fontname="Courier", fontsize=8)
			nodes[i].set_name(insTxt)
			self.graph.add_node(nodes[i])

		ed = pydot.Edge(nodes[0], nodes[1], color=ecolor, label=label, fontname="Courier", fontsize=8, arrowhead="open")
		self.graph.add_edge(ed)

	def draw(self, name, png_mode):
		#self.graph.write(name)
		if png_mode:
			self.graph.write_png(name + ".png")
		else:
			self.graph.write(name + ".dot")

class Block(object):
	""" Sequential group of instructions """
	def __init__(self, parent_class=None, parent_method=None, label=None, instructions=None):
		"""
			Parameters:
				parent_class: Class where our code is located.
				parent_method: Class method where our code is located.
				label: Block identifier (class name[space]method name[space]first line offset).
				instructions: list raw instructions
				targets: Code flow changes targets, if any.
		"""
		self.parent_class = parent_class
		self.parent_method = parent_method
		self.label = label
		self.instructions = instructions
		self.targets = []

	def add_inst(self, inst):
		""" Just add one instruction to our set of instructions. """
		self.instructions.append(inst)

class BlockFactory(object):
	def __init__(self):
		self.blocks = []
		self.ApplicationInventory = []

	def add(self, blk):
		global graph
		""" Add the block to our blocks list if it is not present and have at least one instruction. """
		if (not (blk in self.blocks)) and (len(blk.instructions)>0):
			self.blocks.append(blk)

	def add_before(self, label=None, inst=None, block=None, pclass=None, pmethod=None):
		""" Add instruction to the current block, and then add this to our blocks list. """
		block.add_inst(inst)
		self.add(block)
		return Block(label=label, instructions=[], parent_class=pclass, parent_method=pmethod)

	def add_after(self, label=None, inst=None, block=None, pclass=None, pmethod=None):
		""" Add the block to our list, and make a new one with the specified instructions. """
		self.add(block)
		b = Block(label=label, instructions=[inst], parent_class=pclass, parent_method=pmethod)
		return b

	@staticmethod
	def ApplicationInventory(rdir):
		full_methods = []
		for root, subFolders, files in os.walk(rdir):
			for file in files:
				if file.endswith(".smali"):
					with open(root+"/"+file, "r") as file_handle:
						smali_content = file_handle.read()
						class_search = re.search('\.class\s+(.*?)\n', smali_content)
						class_definition = class_search.group(0)[:-1].split(' ')[-1][:-1]
						method_definitions = re.findall('\.method\s+(.*?)\n', smali_content)
						for method2 in method_definitions:
							full_methods.append("%s->%s" % (class_definition, method2.split(' ')[-1][:-1]) )
		BlockFactory.ApplicationInventory = full_methods
		return full_methods

	@staticmethod
	def xtractBlock(rdir, mdef):
		""" split smali class file into method/s code lines. """
		ndir = "/".join(mdef.split('->')[0][1:-1].split('/')[:-1])
		nfil = mdef.split('->')[0][1:-1].split('/')[-1]
		ndef = mdef.split('->')[1]
		classfile = "%s%s/%s.smali" % (rdir, ndir, nfil)
		functionname = ndef
		# read class file contents
		fh = open(classfile, "r")
		fc = fh.read()
		fh.close()
		# extract method raw lines
		methods = []
		for m in re.findall("\.method\s(.*?)\n(.*?)\.end\smethod", fc, re.DOTALL):
			if functionname is not None:
				if m[0].split(' ')[-1][:-1] == functionname:
					methods.append(m)
					break
			else:
				methods.append(m)
		# remove empty lines
		if len(methods) == 0:
			return None
		else:
			ret = []
			for m in methods:
				instructions = []
				for inst in m[1].split("\n"):
					if len(inst.lstrip())>0:
						instructions.append( inst.lstrip()[:-1] + "\l")
				mname = m[0].split(' ')[-1].split('(')[0]
				ret.append((mname,instructions))
			# All done!
			return ret

	@staticmethod
	def splitBlock(blk, classn, methodn, pos, lenInc, iset, i):
		blockLen = len(blk.instructions) + lenInc
		incrementalLabel = "%s %s %d" % (classn, methodn, pos+blockLen)
		outCall = False
		if re.search("^invoke-", i) == None:
			positionalLabel  = "%s %s %d" % (classn, methodn, iset.index(i.split(' ')[-1])+1 )
		else:
			lindex = int(blk.label.split(' ')[-1]) + len(blk.instructions)
			positionalLabel = " ".join(blk.label.split(' ')[:-1]) + " " + str(lindex+1)
			if i.split(' ')[-1][:-2] in BlockFactory.ApplicationInventory:
				outCall = True
				nfil = i.split('->')[0][1:-1].split('/')[-1]
				ndef = i.split('->')[1].split('(')[0]
				positionalLabel = "%s %s %d"  % (nfil, ndef, 1)
		return (outCall, incrementalLabel, positionalLabel)


def MyOptParser():
	usage = "usage: %prog [options]"
	parser = OptionParser(usage=usage, epilog="""[-d ./smali -m "Lcom/foo/client;->onSuccess(Ljava/lang/String;I)V"]""")
	parser.add_option("-d", action="store", type="string", dest="rootdir",
                  help="Smali code directory entry point.")
	parser.add_option("-m",  action="store", type="string", dest="method",
                  help="Full class method definition string to look for.")

	(options, args) = parser.parse_args()
	if (not options.rootdir):
		parser.error("option -d is mandatory.")
	if (not options.method):
		parser.error("Option -m is mandatory.")
	return options

def findCrossReferences(rdir, mdef):
	definitions = [mdef]
	idx = 0
	while True:
		ndef = definitions[idx]
		ndir = "/".join(ndef.split('->')[0][1:-1].split('/')[:-1])
		nfil = ndef.split('->')[0][1:-1].split('/')[-1]
		ndef = ndef.split('->')[1]
		with open( "%s%s/%s.smali" % (rdir, ndir, nfil) , "r") as fh:
			content = fh.read()
			pdef =  content.find(ndef)
			pdef2 = content.find(".end method", pdef + len(ndef))
			content = content[pdef:pdef2].replace('\r\n\r\n', '\r\n')
			calls = re.findall('invoke-(.*?)\n', content)
			for call in calls:
				if call.split(' ')[-1][:-1] in full_methods:
					if call.split(' ')[-1][:-1] not in definitions:
						definitions.append( call.split(' ')[-1][:-1] )
		idx += 1
		if idx >= len(definitions): break
	return definitions

if __name__ == '__main__':

	options = MyOptParser()
	full_methods = BlockFactory.ApplicationInventory(options.rootdir)

	mdefinition = options.method
	if mdefinition not in full_methods:
		sys.exit("Error: Incorrect parameters.")

	graph_mgr = GraphManager()
	definitions = findCrossReferences(options.rootdir, mdefinition)
	methods = []

	for method in definitions:
		nfil = method.split('->')[0][1:-1].split('/')[-1]
		methodInstructions = BlockFactory.xtractBlock(options.rootdir, method)
		if methodInstructions is not None:
			for mnam, minst in methodInstructions:
				methods.append((nfil, mnam, minst))


	## linear pass 1
	# split method code block into smaller blocks (calls/jumps/conditionals/labeled/catch)
	# calculate block target/s.
	factory = BlockFactory()
	for (cname, mname, minsts) in methods:
		# default initial block
		b = Block(label=cname + " " + mname + " 1", instructions=[], parent_class = cname, parent_method = mname)
		for i2 in minsts:
			instrPos = minsts.index(i2) + 1
			blockPos = int(b.label.split(' ')[-1] )
			if re.search("^goto", i2) != None:
				(outCall, incLabel, posLabel) = BlockFactory.splitBlock(b, cname, mname, blockPos, 1, minsts, i2)
				b.targets = [('jump',posLabel)]
				b = factory.add_before(label=incLabel, inst=i2, block=b, pclass=cname, pmethod=mname)
			elif re.search("^if-", i2) != None:
				(outCall, incLabel, posLabel) = BlockFactory.splitBlock(b, cname, mname, blockPos, 1, minsts, i2)
				b.targets = [('true',posLabel), ('false',incLabel)]
				b = factory.add_before(label=incLabel, inst=i2, block=b, pclass=cname, pmethod=mname)
			elif re.search("^\:" , i2) != None:
				(outCall, incLabel, posLabel) = BlockFactory.splitBlock(b, cname, mname, blockPos, 0, minsts, i2)
				b.targets = [('cont',incLabel)]
				b = factory.add_after(label=incLabel, inst=i2, block=b, pclass=cname, pmethod=mname)
			elif re.search("^.catch ", i2) != None:
				(outCall, incLabel, posLabel) = BlockFactory.splitBlock(b, cname, mname, blockPos, 1, minsts, i2)
				b.targets = [('exception',posLabel), ('try',incLabel)]
				b = factory.add_before(label=incLabel, inst=i2, block=b, pclass=cname, pmethod=mname)
			elif re.search("^invoke-", i2) != None:
				(outCall, incLabel, posLabel) = BlockFactory.splitBlock(b, cname, mname, blockPos, 1, minsts, i2)
				if outCall:
					b.targets = [('call',posLabel), ('on return', incLabel)]
				else:
					b.targets = [('on return',posLabel)]

				b = factory.add_before(label=incLabel, inst=i2, block=b, pclass=cname, pmethod=mname)
			else:
				b.add_inst(i2)
		factory.add(b)

	## linear pass 2
	# joining graph nodes !
	for b1 in factory.blocks:
		for lbl,target in b1.targets:
			for b2 in factory.blocks:
				if b2.label == target:
					graph_mgr.add_edge(b1,b2, lbl)
					break
	fname = options.method.split('->')[1].split('(')[0]
	graph_mgr.draw(fname, True)
