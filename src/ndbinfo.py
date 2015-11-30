#!/usr/bin/env python

# ndbinfo.py -- X3D Type Hierarchy Information Tool
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

nodeDB = None

def getAllBases(node, basesList, virtualBasesList):
    superNodes = node.getSuperNodes()
    
    for n in superNodes:
        if n in basesList:
            if n not in virtualBasesList:
                virtualBasesList.append(n)
        else:
            basesList.append(n)
            getAllBases(n, basesList, virtualBasesList)

def getAllDerivedNodes(node, derivedList):
    derivedNodes = node.getDerivedNodes()
    for n in derivedNodes:
        if n not in derivedList:
            derivedList.append(n)
            getAllDerivedNodes(n, derivedList)

def findFirstFieldDeclNodes(node, fieldName):
    if node.findField(fieldName) is None:
        return []
    result = []
    for n in node.getSuperNodes():
        result.extend(findFirstFieldDeclNodes(n, fieldName))
    if len(result) == 0:
        result = [node]
    return result

def error(msg, exitCode = 1, exit = True):
    sys.stderr.write('Error: ')
    sys.stderr.write(msg)
    sys.stderr.write('\n')
    if exit:
        sys.exit(exitCode)

### Node Checker ###

def equalFields(f1, f2):
    return f1.type == f2.type and \
           f1.accessType == f2.accessType and \
           f1.name == f2.name


def checkFieldSet(node, fieldNodeDict, errors):
    global nodeDB

    superNodes = node.getSuperNodes()
    fieldSuperNodeDict = {}
    for n in superNodes:
        checkFieldSet(n, fieldSuperNodeDict, errors)

    # check fields of this node which are already defined in one
    # of the super nodes
    superFieldNames = []
    for fieldName, fieldAndNode in fieldSuperNodeDict.items():

        superFieldNames.append(fieldName)

        f = node.findField(fieldName)
        if f is None:
            errors.append('Field %s declared in the node "%s" is not declared in node "%s"' % (fieldName, fieldAndNode[1].getType(), node.getType()))
            continue
        if not equalFields(f, fieldAndNode[0]):
            errors.append('Field %s defined in the node "%s" differ to the declaration in node "%s"' % (fieldName, fieldAndNode[1].getType(), node.getType()))
            errors.append('  in %s : %s' % (fieldAndNode[1].getType(), fieldAndNode[0]))
            errors.append('  in %s : %s' % (node.getType(), f))
            

    # check all SFNode/MFNode fields for incorrect validValueTypes
    for field in node.getFields():
        if field.getName() not in superFieldNames:
        
            if field.getType() in ('SFNode', 'MFNode'):
                for valueType in field.getValidValueTypes():
                    if not nodeDB.getNode(valueType):
                        errors.append('Field %s defined in the node "%s" refer to unknown node type "%s" in the valid node type list' % (field.getName(), node.getType(), valueType))
        
    
    # update fieldNodeDict
    fieldNodeDict.update(fieldSuperNodeDict)
    for field in node.getFields():
        if not fieldNodeDict.has_key(field.getName()):
            fieldNodeDict[field.getName()] = (field, node)

def checkNode(node, errors):
    assert len(node.getSuperNodes()) == len(node.getSuperTypes())
    fieldNodeDict = {}
    checkFieldSet(node, fieldNodeDict, errors)

####################

def usage(exitCode = 0):
    print 'Usage:',sys.argv[0],'[options] <node-db-file>'
    print '-h | --help                     Print this message and exit.'
    print '-n | --node-types list          Output info only for specified node types list separated by commas'
    print '-l | --list                     Print nodes in the X3D specification format'
    print '-c | --check                    Check node database for errors'
    print '-i | --info                     Print node information'
    print '-s | --sort                     Sort node list on type name'
    print '-b | --bases                    Print bases (super types)'
    print '-v | --virtual-bases            Print virtual bases'
    print '-d | --derived                  Print nodes derived from all nodes from the specified node list (set intersection)'
    print '--list-components               Print list of all components'
    print '--list-nodes-of-component component-name'
    print '                               Print list of all nodes that' \
          'belongs to the specified component'
    sys.exit(exitCode)

def main():
    global nodeDB
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hn:clisbvd',
                                   ['help', 'nodes-types=',
                                    'check', 'list', 'info', 'sort', 'bases',
                                    'virtual-bases', 'derived',
                                    'list-components',
                                    'list-nodes-of-component='])
    except getopt.GetoptError, e:
        error(str(e), exit = False)
        usage(1)

    listNodes = False
    checkNodes = False
    printInfo = False
    sortNodes = False
    printBases = False
    printVirtualBases = False
    printDerivedNodes = False
    listComponents = False

    nodeTypes = []
    listNodesOfComponent = []

    exitCode = 0

    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
        elif o in ('-c', '--check'):
            checkNodes = True
        elif o in ('-l', '--list'):
            listNodes = True
        elif o in ('-i', '--info'):
            printInfo = True
        elif o in ('-s', '--sort'):
            sortNodes = True
        elif o in ('-b', '--bases'):
            printBases = True
        elif o in ('-v', '--virtual-bases'):
            printVirtualBases = True
        elif o in ('-n', '--node-types'):
            nodeTypes.extend(a.split(','))
        elif o in ('-d', '--derived'):
            printDerivedNodes = True
        elif o in ('--list-components',):
            listComponents = True
        elif o in ('--list-nodes-of-component',):
            listNodesOfComponent.extend(a.split(','))

    if len(args) != 1:
        error('you must specify node database file')

    f = args[0]
    print >>sys.stderr, 'NodeDB file:', f

    fd = open(f, 'r')
    nodeDB = pickle.load(fd)
    fd.close()

    nodeDB.updateHierarchy()

    numNodes = len(nodeDB.getNodeList())
    numAbstractNodes = 0
    for n in nodeDB.getNodeList():
        if n.isAbstract():
            numAbstractNodes+=1

    print >>sys.stderr, '%i concrete nodes' % (numNodes-numAbstractNodes)
    print >>sys.stderr, '%i abstract nodes' % numAbstractNodes
    print >>sys.stderr, '%i nodes in total' % numNodes

    if not nodeTypes:
        nodeList = nodeDB.getNodeList()
    else:
        nodeList = []
        for nt in nodeTypes:
            node = nodeDB.getNode(nt)
            if node:
                nodeList.append(node)
            else:
                print >>sys.stderr, 'Unknown node "%s"' % nt

    if checkNodes:
        for node in nodeList:
            errors = []
            checkNode(node, errors)
            if len(errors) > 0:
                print '=== Errors in node %s ===' % node.getType()
                for err in errors:
                    print err
                exitCode = 1

    if listNodes:
        specFile = None

        if sortNodes:
            nodeList = nodeList[:]
            nodeList.sort(cmp=lambda x,y:cmp(x.getType(),y.getType()))
        
        for node in nodeList:
            if node.getSpecFile() != specFile:
                specFile = node.getSpecFile()
                print '# file : %s' % specFile
                print
            print node
            print
            
    if printInfo:
        for node in nodeList:
            print '=== %s ===' % node.getType()

            # type accessTypeName name value validValueTypes
            maxLen = [0, 0, 0, 0, 0]
            myLen = lambda s: len(s or ())
            for field in node.getFields():
                maxLen[0] = max(maxLen[0], myLen(field.type))
                maxLen[1] = max(maxLen[1], myLen(field.getAccessTypeName()))
                maxLen[2] = max(maxLen[2], myLen(field.name))
                maxLen[3] = max(maxLen[3], myLen(field.value))
                maxLen[4] = max(maxLen[4], myLen(field.getValidValueTypesStr()))

            fieldStr = []
            declFieldNodes = []
            maxFieldStrLen = 0

            for field in node.getFields():
                fs = field.toString(*maxLen)
                fieldStr.append(fs)
                maxFieldStrLen = max(len(fs), maxFieldStrLen)
                declFieldNodes.append(findFirstFieldDeclNodes(node, field.getName()))

            for i in xrange(len(fieldStr)):
                fs = fieldStr[i]
                declNodes = declFieldNodes[i]
                print '%s declared in %s' % (fs.ljust(maxFieldStrLen), ','.join([n.getType() for n in declNodes]))
        
    if printBases or printVirtualBases:
        for node in nodeList:
            bases = []
            virtualBases = []
            getAllBases(node, bases, virtualBases)

            if (printBases and bases) or (printVirtualBases and virtualBases):
                print '=== %s ===' % (node.getType())
            
            if printBases and bases:
                print '* Bases *'
                for b in bases:
                    print b.getType()
            if printVirtualBases and virtualBases:
                print '* Virtual bases *'
                for b in virtualBases:
                    print b.getType()

    if printDerivedNodes:
        from sets import Set
        
        derivedNodeSet = None
        for node in nodeList:
            derivedNodes = []
            getAllDerivedNodes(node, derivedNodes)
            if derivedNodeSet is None:
                derivedNodeSet = Set(derivedNodes)
            else:
                derivedNodeSet = derivedNodeSet.intersection(derivedNodes)
            
        print '=== All nodes derived from %s node(s) ===' % \
              (','.join([n.getType() for n in nodeList]))
        
        if len(derivedNodeSet):
            for n in derivedNodeSet:
                print n.getType()
        else:
            print 'No nodes'

    if listComponents:
        components = {}
        for n in nodeDB.getNodeList():
            componentName = n.getComponentName()
            if componentName not in components:
                components[componentName] = True
                print componentName

    if listNodesOfComponent:
        for n in nodeDB.getNodeList():
            if n.getComponentName() in listNodesOfComponent:
                print n.getType()

    sys.exit(exitCode)

if __name__ == '__main__':
    main()
