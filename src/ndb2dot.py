#!/usr/bin/env python

# ndb2dot.py -- X3D Type Hierarchy to Graphviz dot Format Converter
#
# Author: Dmitri Rubinstein <rubinstein@cs.uni-saarland.de>
#
# Copyright (C) 2008 Saarland University
# Copyright (C) 2009, 2010, 2011, 2012 German Research Center for
# Artificial Intelligence (DFKI)
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
import getopt
import cPickle as pickle

##########################################################################
# DotExporter
##########################################################################

class DotExporter(object):

    def __init__(self, nodeDB, nodes=None):
        self.nodeDB = nodeDB
        if isinstance(nodes, str):
            self.nodes = [nodes]
        else:
            self.nodes = nodes
        self.nodeList = None
        self.inverseHierarchy = False
        self.clusterComponents = True

    def _getAllSuperNodes(self, node, nodeList):
        superNodes = []
        for t in node.getSuperTypes():
            superNodes.append(self.nodeDB.getNode(t))
        for sn in superNodes:
            if sn not in nodeList:
                nodeList.append(sn)
        for sn in superNodes:
            self._getAllSuperNodes(sn, nodeList)

    def _computeNodeList(self):
        if self.nodes is None or len(self.nodes) == 0:
            self.nodeList = self.nodeDB.getNodeList()
        else:
            self.nodeList = []
            for nodeType in self.nodes:
                node = self.nodeDB.getNode(nodeType)
                if node:
                    self.nodeList.append(node)
                    self._getAllSuperNodes(node, self.nodeList)

    def _createComponentList(self):
        components = {}
        for node in self.nodeList:
            cn = node.getComponentName()
            cnl = components.get(cn, None)
            if cnl == None:
                cnl = []
                components[cn] = cnl
            cnl.append(node)
        return components

    def getDotAttrs(self, node):
        attrs = ''
        if node.isAbstract():
            attrs += 'fontname="Times-Italic"'
        return attrs

    def export(self, out):
        self._computeNodeList()
        
        print >>out, 'digraph {'
        print >>out, 'concentrate=true;'
        components = self._createComponentList()
        
        for cn, cnl in components.items():
            name = cn.replace('-', '_')
            print >>out, 'subgraph cluster_%s {' % name
            for node in cnl:
                print >>out, '%s [ %s ];' % (node.getType(), self.getDotAttrs(node))
            print >>out, 'label = "%s";' % cn
            print >>out, 'color = blue;'
            print >>out, '}'

        if self.inverseHierarchy:
            for node in self.nodeList:
                pc = ';'.join(node.getSuperTypes())
                print >>out, '%s -> { %s }' % (node.getType(), pc)
        else:
            for node in self.nodeList:
                derivedNodes = [n for n in node.getDerivedNodes() if n in self.nodeList]
                
                pc = ';'.join([n.getType() for n in derivedNodes])
                print >>out, '%s -> { %s }' % (node.getType(), pc)
            
        print >>out, '}'

def error(msg, exitCode = 1, exit = True):
    sys.stderr.write('Error: ')
    sys.stderr.write(msg)
    sys.stderr.write('\n')
    if exit:
        sys.exit(exitCode)

def usage(exitCode = 0):
    print 'Usage:',sys.argv[0],'[options] <node-db-file>'
    print '-h | --help                     Print this message and exit.'
    print '-n | --node-types list          Output hierarchy of specified node types (list is separated by commas)'
    sys.exit(exitCode)

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hn:',
                                   ['help', 'node-types='])
    except getopt.GetoptError, e:
        error(str(e), exit = False)
        usage(1)

    nodes = []

    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
        elif o in ('-n', '--node-types'):
            nodes.extend(a.split(','))

    if len(args) != 1:
        error('you must specify node database file')

    f = args[0]
    print >>sys.stderr, 'NodeDB file:', f

    fd = open(f, 'r')
    nodeDB = pickle.load(fd)
    fd.close()

    nodeDB.updateHierarchy()

    de = DotExporter(nodeDB, nodes)
    de.export(sys.stdout)

if __name__ == '__main__':
    main()
