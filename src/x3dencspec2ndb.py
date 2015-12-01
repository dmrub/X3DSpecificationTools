#!/usr/bin/env python

# x3dencspec2ndb.py -- Extract Node Information from X3D Encoding Specification
#
# Author: Dmitri Rubinstein <dmitri.rubinstein@dfki.de>
#
# Copyright (C) 2015 German Research Center for Artificial Intelligence (DFKI)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import sys
import os
import os.path
import getopt
import re
from nodedb import *
import cPickle as pickle
from lxml import html

DEBUG_MODE = False


def debug(msg):
    global DEBUG_MODE
    if DEBUG_MODE:
        print >> sys.stderr, msg


def error(msg, exitCode=1, exit=True):
    sys.stderr.write('Error: ')
    sys.stderr.write(msg)
    sys.stderr.write('\n')
    if exit:
        sys.exit(exitCode)


class ParsingException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return 'ParsingException: ' + str(self.message)


KEY_VALUE_PATTERN = re.compile(r'''\s*([a-zA-Z_][a-zA-Z0-9_]*)=("(?:[^"\\]|\\[\\"]?)*")''')


##########################################################################
# X3DEncSpecParser
##########################################################################

class X3DEncSpecParser:
    def __init__(self, nodeDB):
        self.nodeDB = nodeDB
        self.collectedErrors = []

    def parsingError(self, e):
        self.collectedErrors.append(e)

    def getNodeDB(self):
        return self.nodeDB

    def parseEncodingOfNodes(self, encodingOfNodesPath):
        debug('processing file %s' % encodingOfNodesPath)
        tree = html.parse(encodingOfNodesPath)
        nodeSpecs = tree.xpath("//table[@class=\"nodes\"]")
        for ns in nodeSpecs:
            summary = ns.get('summary')
            nodeNames = ns.xpath('tbody/tr/td[@class=\"node1\"]/b')
            if not nodeNames or len(nodeNames) < 1:
                self.parsingError(ParsingException('Unexpected node structure, expected at least one <b> tag: %s' %
                                                   ' '.join([html.tostring(e) for e in nodeNames])))
                continue
            nodeName = nodeNames[0].text_content()
            if not nodeName.startswith('<'):
                self.parsingError(ParsingException(
                    'Unexpected node structure, first node name should start with "<": %s' % nodeName))
                continue
            nodeName = nodeName[1:]
            if summary:
                if nodeName not in summary:
                    self.parsingError(
                        ParsingException('Unexpected node structure, node name "%s" is not contained in summary "%s"' %
                                         (nodeName, summary)))
            spec = ns.xpath('tbody/tr/td/div[@class=\"nodes\"]')
            specText = ''
            for e in spec:
                specText += e.text_content().encode('utf-8').strip() \
                                .replace('\r', '\n').replace('\xc2', ' ').replace('\xa0', ' ') + '\n'
            kvMap = {}
            for e in specText.split('\n'):
                er = e.strip()
                if len(er) != 0:
                    m = KEY_VALUE_PATTERN.match(er)
                    if m:
                        key = m.group(1)
                        value = m.group(2)
                        value = value[1:-1]
                        # unescape escaped characters
                        value = value.replace('\\\\', '\\').replace('\\"', '"')
                        kvMap[key] = value
            node = self.nodeDB.getNode(nodeName)
            if node:
                containerFieldName = kvMap.get('containerField')
                if containerFieldName:
                    node.setContainerField(containerFieldName)

    def finishParsing(self):
        self.nodeDB.updateHierarchy()


def usage(exitCode=0):
    print 'Usage:', sys.argv[0], '[options] <path-to-x3d-encoding-spec> <node-db-file>'
    print '-h | --help                     Print this message and exit.'
    print '-p | --pickle                   Output node database in pickle format'
    print '-e | --errors                   Print all parsing errors to stderr'
    print '-d | --debug                    Debug mode'
    sys.exit(exitCode)


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hped',
                                   ['help', 'pickle', 'errors', 'debug'])
    except getopt.GetoptError, e:
        error(str(e), exit=False)
        usage(1)

    pickleNodeDB = False
    printErrors = False
    global DEBUG_MODE

    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
        elif o in ('-p', '--pickle'):
            pickleNodeDB = True
        elif o in ('-e', '--errors'):
            printErrors = True
        elif o in ('-d', '--debug'):
            DEBUG_MODE = True

    if len(args) != 2:
        error('you must specify path to X3D encoding specification and node database file')

    pathToSpec = args[0]
    print >> sys.stderr, 'Path to X3D specification:', pathToSpec
    nodeDBFile = args[1]
    print >> sys.stderr, 'NodeDB file:', nodeDBFile

    fd = open(nodeDBFile, 'r')
    nodeDB = pickle.load(fd)
    fd.close()

    parser = X3DEncSpecParser(nodeDB)

    encodingOfNodesPath = os.path.join(pathToSpec, 'Part01', 'EncodingOfNodes.html')

    if not os.path.exists(encodingOfNodesPath):
        error('Path %s does not exists.' % encodingOfNodesPath)

    parser.parseEncodingOfNodes(encodingOfNodesPath)

    parser.finishParsing()

    nodeDB = parser.getNodeDB()

    if pickleNodeDB:
        pickle.dump(nodeDB, sys.stdout)
    else:
        specFile = None
        for node in nodeDB.getNodeList():
            if node.getSpecFile() != specFile:
                specFile = node.getSpecFile()
                print '# file : %s' % specFile
                print
            print node
            print

    if printErrors:
        for e in parser.collectedErrors:
            print >> sys.stderr, e
        if len(parser.collectedErrors):
            sys.exit(1)


if __name__ == '__main__':
    main()
