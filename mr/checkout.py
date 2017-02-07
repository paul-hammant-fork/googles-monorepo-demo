#!/usr/bin/python
import os
import sys
from subprocess import call

def needThis(neededModule, depMap, neededModules2):
    if neededModule in depMap:
        for dependency in depMap[neededModule]:
            needThis(dependency, depMap, neededModules2)
    neededModules2[neededModule] = True

def writepom(pom_template):
    dirname = os.path.dirname(pom_template)
    with open(pom_template) as f:
        if os.path.exists(dirname + '/pom.xml'):
            os.chmod(dirname + '/pom.xml', 0755)
        with open(dirname + '/pom.xml', 'w') as the_pom:
            lines = f.readlines()
            for line in lines:
                if line.strip().startswith("<module>") and line.strip().endswith("</module>"):
                    sub_project = line.strip()[8:]
                    sub_project = sub_project[:sub_project.index("<")]
                    f_path = dirname + "/" + sub_project
                    if os.path.exists(f_path + '/pom.xml') or os.path.exists(f_path + '/pom-template.xml'):
                        the_pom.write(line)
                else:
                    the_pom.write(line)
        os.chmod(dirname + '/pom.xml', 0444)


neededModules = {}
depMap = {}

# passed in args into dict
for ix, arg in enumerate(sys.argv):
    if ix > 0:
        neededModules[arg] = True

# crunch dot graph into Python dict
with open("dependency-graph.dot") as dot:
    lines = dot.readlines()
    for line in lines:
        line = line.replace("\"","")
        if " -> " in line:
            parts = line.split(" -> ")
            lpart = parts[0].split(":")[1]
            rpart = parts[1].split(":")[1]
            if lpart not in depMap:
                depMap[lpart] = {}
                depMap[lpart][rpart] = True

    # penultimate list of deps we need, tree into flat
    neededModules2 = {}
    for neededModule in neededModules:
        needThis(neededModule, depMap, neededModules2)

    # we always need these
    sparse_checkout = "/mr/*\n/README.md\n/all_poms.txt\n/dependency-graph.dot\n/pom-template.xml\n"

    with open("all_poms.txt") as allpoms:
        lines = allpoms.readlines()
        for line in lines:
            hit = False
            for neededModule in neededModules2:
                if "/"+neededModule+"/" in line:
                    sparse_checkout += line[1:]
                    sparse_checkout += line[1:].replace("pom-template.xml","src/*")
                    # some weird Google-Guava non-maven-standard layout
                    sparse_checkout += line[1:].replace("pom-template.xml","benchmark/*")
                    sparse_checkout += line[1:].replace("pom-template.xml","test/*")
                    sparse_checkout += line[1:].replace("pom-template.xml","src-super/*")

        # Redo sparse-checkout file
        with open('.git/info/sparse-checkout', 'w') as sc:
            sc.write(sparse_checkout)

        # Remove old pom files
        for root, dirs, files in os.walk("."):
            for currentFile in files:
                if currentFile.endswith("/pom.xml"):
                    os.remove(os.path.join(root, currentFile))

        # sparse re-checkout
        call(["git", "checkout", "--"])

        # Write new pom files if approriate
        for root, dirs, files in os.walk("."):
            for currentFile in files:
                fullpath = os.path.join(root, currentFile)
                if fullpath.endswith("/pom-template.xml"):
                    writepom(fullpath)
