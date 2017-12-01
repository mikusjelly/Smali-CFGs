import os
import re


class Walker:
    def __init__(self, location):
        self.location = location
        self.AppInventory = {}
        self.ParsedResults = None
        self.Finder = None
        self.do_walk()

    def assign_finder(self, finder):
        self.Finder = finder

    def do_find(self):
        return self.Finder.do_find(self.AppInventory)

    def do_walk(self):
        self.AppInventory = {}
        ptn1 = r'^\.class.*?\s(L.*?;)\s*?\.super\s+(L.*?;)\s*?\.source\s+"(.*?)"'
        prog1 = re.compile(ptn1)

        ptn2 = r'(\.field\s+.*)'
        prog2 = re.compile(ptn2)

        ptn3 = r'\.method\s(.*)\s+?([.\s\S]*?)\.end\s+method'
        prog3 = re.compile(ptn3)

        for root, _, files in os.walk(self.location):
            for file in files:
                if not file.endswith(".smali"):
                    continue

                with open(os.path.join(root, file), "r") as file_handle:
                    content = file_handle.read()

                    groups = prog1.search(content).groups()

                    class_name = groups[0]

                    self.AppInventory[class_name] = {}
                    self.AppInventory[class_name]['Properties'] = prog2.findall(
                        content, re.MULTILINE)

                    self.AppInventory[class_name]['Methods'] = []
                    for m in prog3.findall(content, re.MULTILINE):
                        ind_meth = {}
                        ind_meth['Name'] = m[0].split(' ')[-1]
                        ind_meth['Instructions'] = []
                        for i in m[1].split('\r\n'):
                            if i:
                                ind_meth['Instructions'].append(
                                    i.lstrip().rstrip())
                        self.AppInventory[class_name]['Methods'].append(
                            ind_meth)
