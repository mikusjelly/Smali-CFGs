import re


class CallsFinder(object):
    def __init__(self, what):
        self.methods = what

    def do_find(self, where):
        co = []
        for class_name in where:
            for mth_dict in where[class_name]['Methods']:
                caller = "%s->%s" % (class_name, mth_dict['Name'])
                block = '\r\n'.join(mth_dict['Instructions'])

                results = re.findall(
                    r'invoke-.*?\s.*?, (L.*?)$', block, re.M)

                for invoke in results:
                    called = invoke
                    if (caller in self.methods) or (called in self.methods):
                        co.append((caller, called))
        return co
