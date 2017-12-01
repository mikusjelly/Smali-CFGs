import re


class Block(object):
    ''' Secuencia de instrucciones '''

    def __init__(self, clase_padre=None, metodo_padre=None, etiqueta=None, instrucciones=None):
        '''
                instrucciones que forman el bloque.
                Método al que pertenecen.
                Clase del método.
                Etiqueta identificativa.
                Bifurcaciones.
        '''
        self.clase_padre = clase_padre
        self.metodo_padre = metodo_padre
        self.etiqueta = etiqueta
        self.instrucciones = instrucciones
        self.bifurcaciones = []

    def add_inst(self, inst):
        self.instrucciones.append(inst)


class InstructionsFinder(object):
    def __init__(self, what, how=False):
        self.method = what
        self.calls_inventory = {}
        self.ParsedResults = []
        self.full = how

    def _define_inventory(self, where):
        for class_name in where:
            for mth_dict in where[class_name]['Methods']:
                caller = "%s->%s" % (class_name, mth_dict['Name'])
                block = '\n'.join(mth_dict['Instructions'])
                self.calls_inventory[caller] = []
                for invoke in re.findall('invoke-(.*?)\n', block, re.DOTALL):
                    called = invoke.split(' ')[-1]
                    if caller in self.calls_inventory:
                        self.calls_inventory[caller].append(called)

    def _get_xrefs(self):
        calls_to_review = [self.method]
        analized_calls = []
        nMethods = 0
        while True:
            mname = calls_to_review[nMethods]
            for called in self.calls_inventory[mname]:
                if (mname, called) not in analized_calls:
                    if called not in calls_to_review:
                        if called in self.calls_inventory:
                            calls_to_review.append(called)
                        analized_calls.append((mname, called))

            nMethods += 1
            if nMethods >= len(calls_to_review):
                break
        return calls_to_review

    def _get_method_instructions(self, method, where):
        class_name = method.split('->')[0]
        if class_name not in where:
            return None
        method_name = method.split('->')[1]
        for mth_dict in where[class_name]['Methods']:
            if mth_dict['Name'] == method_name:
                insts = []
                for i in mth_dict['Instructions']:
                    if i:
                        insts.append(i.lstrip() + "\l")
                return (class_name, method_name, insts)
        return None

    def _splitBlock(self, blk, classn, methodn, pos, lenInc, iset, i):
        blockLen = len(blk.instrucciones) + lenInc
        incrementaletiqueta = "%s %s %d" % (classn, methodn, pos + blockLen)
        outCall = False

        if re.search("^invoke-", i) == None:
            positionaletiqueta = "%s %s %d" % (
                classn, methodn, iset.index(i.split(' ')[-1]) + 1)
        else:
            lindex = int(blk.etiqueta.split(' ')[-1]) + len(blk.instrucciones)
            positionaletiqueta = " ".join(blk.etiqueta.split(' ')[
                                          :-1]) + " " + str(lindex + 1)
            if i.split(' ')[-1][:-2] in list(self.calls_inventory.keys()):
                outCall = True
                nfil = i.split('->')[0].split(' ')[-1]
                ndef = i.split('->')[1][:-2]
                positionaletiqueta = "%s %s %d" % (nfil, ndef, 1)

        return (outCall, incrementaletiqueta, positionaletiqueta)

    def _genBlockList(self, methods):
        for (cname, mname, minsts) in methods:
            # default initial block
            b = Block(etiqueta=cname + " " + mname + " 1",
                      instrucciones=[], clase_padre=cname, metodo_padre=mname)
            for i2 in minsts:
                instrPos = minsts.index(i2) + 1
                blockPos = int(b.etiqueta.split(' ')[-1])
                if re.search("^goto", i2) != None:
                    (outCall, incetiqueta, posetiqueta) = self._splitBlock(
                        b, cname, mname, blockPos, 1, minsts, i2)
                    b.bifurcaciones = [('jump', posetiqueta)]
                    b = self.add_before(
                        etiqueta=incetiqueta, inst=i2, block=b, pclass=cname, pmethod=mname)
                elif re.search("^if-", i2) != None:
                    (outCall, incetiqueta, posetiqueta) = self._splitBlock(
                        b, cname, mname, blockPos, 1, minsts, i2)
                    b.bifurcaciones = [('true', posetiqueta),
                                       ('false', incetiqueta)]
                    b = self.add_before(
                        etiqueta=incetiqueta, inst=i2, block=b, pclass=cname, pmethod=mname)
                elif re.search("^\:", i2) != None:
                    (outCall, incetiqueta, posetiqueta) = self._splitBlock(
                        b, cname, mname, blockPos, 0, minsts, i2)
                    b.bifurcaciones = [('cont', incetiqueta)]
                    b = self.add_after(
                        etiqueta=incetiqueta, inst=i2, block=b, pclass=cname, pmethod=mname)
                elif re.search("^.catch ", i2) != None:
                    (outCall, incetiqueta, posetiqueta) = self._splitBlock(
                        b, cname, mname, blockPos, 1, minsts, i2)
                    b.bifurcaciones = [
                        ('exception', posetiqueta), ('try', incetiqueta)]
                    b = self.add_before(
                        etiqueta=incetiqueta, inst=i2, block=b, pclass=cname, pmethod=mname)
                elif re.search("^invoke-", i2) != None:
                    (outCall, incetiqueta, posetiqueta) = self._splitBlock(
                        b, cname, mname, blockPos, 1, minsts, i2)
                    if outCall:
                        b.bifurcaciones = [
                            ('call', posetiqueta), ('on return', incetiqueta)]
                    else:
                        b.bifurcaciones = [('on return', posetiqueta)]
                    b = self.add_before(
                        etiqueta=incetiqueta, inst=i2, block=b, pclass=cname, pmethod=mname)
                else:
                    b.add_inst(i2)
            self.add(b)

    def add(self, blk):
        """ Add the block to our blocks list if it is not present and have at least one instruction. """
        if (not (blk in self.ParsedResults)) and (len(blk.instrucciones) > 0):
            self.ParsedResults.append(blk)

    def add_before(self, etiqueta=None, inst=None, block=None, pclass=None, pmethod=None):
        """ Add instruction to the current block, and then add this to our blocks list. """
        block.add_inst(inst)
        self.add(block)
        return Block(etiqueta=etiqueta, instrucciones=[], clase_padre=pclass, metodo_padre=pmethod)

    def add_after(self, etiqueta=None, inst=None, block=None, pclass=None, pmethod=None):
        """ Add the block to our list, and make a new one with the specified instrucciones. """
        self.add(block)
        return Block(etiqueta=etiqueta, instrucciones=[inst], clase_padre=pclass, metodo_padre=pmethod)

    def do_find(self, where):
        class_name = self.method.split('->')[0]
        if class_name not in where:
            return []
        self._define_inventory(where)
        nodes = self._get_xrefs()
        methods = []
        for method in nodes:
            methodinsts = self._get_method_instructions(method, where)
            if methodinsts is not None:
                if methodinsts not in methods:
                    if self.full:
                        methods.append(methodinsts)
                    elif method.startswith(class_name):
                        methods.append(methodinsts)

        self._genBlockList(methods)
        return self.ParsedResults
