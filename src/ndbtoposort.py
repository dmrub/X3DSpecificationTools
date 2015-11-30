#!/usr/bin/env python

# ndbtoposort.py -- X3D Type Hierarchy Topological Sort
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
import nodedb

def usage(exitCode = 0):
    print 'Usage:',sys.argv[0],'[options] <node-db-file>'
    print '-h | --help                     Print this message and exit.'
    sys.exit(exitCode)

def error(msg, exitCode = 1, exit = True):
    sys.stderr.write('Error: ')
    sys.stderr.write(msg)
    sys.stderr.write('\n')
    if exit:
        sys.exit(exitCode)

WHITE_COLOR = 0
BLACK_COLOR = 1
GREY_COLOR  = 2


class ValueRef:

    def __init__(self, value):
        self.value = value

class Vertex:

    def __init__(self, node):
        self.node = node
        self.adjacentVertices = []
        self.color = WHITE_COLOR
        self.discoverTime = -1
        self.finishTime = -1

    def getNode(self):
        return node

    def isAdjacentNode(self, node):
        for v in self.adjacentVertices:
            if v.node == node:
                return True
        return False

    def getTypeName(self):
        return self.node.getType()

    def addAdjacentVertex(self, vertex):
        if vertex not in self.adjacentVertices:
            self.adjacentVertices.append(vertex)
            return True
        return False

    def getAdjacentVertices(self):
        return self.adjacentVertices

class Graph:

    def __init__(self):
        # node name : vertex
        self.vertices = {}

    def getVertex(self, nameOrNode):
        if isinstance(nameOrNode, nodedb.Node):
            return self.vertices.get(nameOrNode.getType(), None)
        return self.vertices.get(nameOrNode, None)

    def getOrCreateVertex(self, node):
        vertex = self.getVertex(node)
        if not vertex:
            vertex = Vertex(node)
            self.vertices[node.getType()] = vertex
        return vertex

    def addEdge(self, srcNodeOrVertex, destNodeOrVertex):
        if isinstance(srcNodeOrVertex, Vertex):
            srcVertex = srcNodeOrVertex
        else:
            srcVertex = self.getOrCreateVertex(srcNodeOrVertex)
            
        if isinstance(destNodeOrVertex, Vertex):
            destVertex = destNodeOrVertex
        else:
            destVertex = self.getOrCreateVertex(destNodeOrVertex)
            
        return srcVertex.addAdjacentVertex(destVertex)

    def __str__(self):
        s = ''
        for v in self.vertices.values():
            for u in v.getAdjacentVertices():
                s+='(%s, %s)\n' % (v.getTypeName(), u.getTypeName())
        return s

    def beginDFS(self):
        for u in self.vertices.values():
            u.color = WHITE_COLOR


    def visitDFS(self, u, time, discoverFunc=None, finishFunc=None):
        """u - vertex"""
        u.color = GREY_COLOR
        time.value += 1
        u.discoverTime = time.value
        if discoverFunc:
            discoverFunc(u)
        for v in u.getAdjacentVertices(): # Explore edge (u, v)
            if v.color == WHITE_COLOR:
                self.visitDFS(v, time, discoverFunc, finishFunc)
            elif v.color == GREY_COLOR:
                print "Back edge (%s, %s)" % (u.getTypeName(), v.getTypeName())
        u.color = BLACK_COLOR
        time.value += 1
        u.finishTime = time.value
        if finishFunc:
            finishFunc(u)

    def DFS(self, discoverFunc=None, finishFunc=None):
        self.beginDFS()
        time = ValueRef(0)
        for u in self.vertices.values():
            if u.color == WHITE_COLOR:
                self.visitDFS(u, time, discoverFunc, finishFunc)

        

    def topologicalSort(self):
        topoList = []

        def addVertex(vertex):
            topoList.insert(0, vertex)

        self.DFS(finishFunc=addVertex)

        return topoList

def topologicalSort(ndb):
    g = Graph()
    
    for n in ndb.getNodeList():
        # Process super types
        for sn in n.getSuperNodes():
            g.addEdge(sn, n)
            
        # Process node fields
        for f in n.getOwnFields():
            if f.getType() in ('SFNode', 'MFNode'):
                for t in f.getValidValueTypes():
                    tn = ndb.getNode(t)
                    if not tn:
                        print 'Error: Unknown node type "%s" in field "%s" of node "%s",  ignored.' % (t, f, n.getType())
                    else:
                        r = g.addEdge(tn, n)

    print 'Graph'
    print g

    print [v.getTypeName() for v in g.topologicalSort()]
    

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'h',
                                   ['help'])
    except getopt.GetoptError, e:
        error(str(e), exit = False)
        usage(1)

    nodes = []

    for o, a in opts:
        if o in ('-h', '--help'):
            usage()

    if len(args) != 1:
        error('you must specify node database file')

    f = args[0]
    print >>sys.stderr, 'NodeDB file:', f

    ndb = nodedb.load(f)
    topologicalSort(ndb)
    

if __name__ == '__main__':
    main()
