class StringsFinder(object):

    def __init__(self, what):
        self.limitations = ['.field', '.local',
                            '.param', 'const-string', 'sput', 'sget']
        self.patterns = what

    def do_find(self, where):
        co = {}
        for class_name in where:
            for mth_dict in where[class_name]['Methods']:
                for inst in mth_dict['Instructions']:
                    for pattern in self.patterns:
                        if pattern.lower() not in inst.lower():
                            continue

                        for lim in self.limitations:
                            if lim not in inst.lower():
                                continue

                            method_definition = "%s->%s" % (
                                class_name, mth_dict['Name'])
                            if method_definition in co:
                                if inst not in co[method_definition]:
                                    co[method_definition].append(inst)
                            else:
                                co[method_definition] = [inst]
        return co
