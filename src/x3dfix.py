#!/usr/bin/env python

# x3dfix.py -- Fix ISO X3D Specification Edition 2
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
    print 'Usage:',sys.argv[0],'[options] [<node-db-file>]'
    print '-h | --help                     Print this message and exit.'
    sys.exit(exitCode)

def error(msg, exitCode = 1, exit = True):
    sys.stderr.write('Error: ')
    sys.stderr.write(msg)
    sys.stderr.write('\n')
    if exit:
        sys.exit(exitCode)

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

    if len(args) > 0:
        f = args[0]
        fn = f
    else:
        f = sys.stdin
        fn = 'stdin'

    print >>sys.stderr, 'x3dfix.py: Fixing NodeDB file:', fn

    ndb = nodedb.load(f)

    # Fixing

    # GeoMetadata

    # remove 'urn' from valid value types list
    
    n = ndb.getNode('GeoMetadata')
    f = n.findField('data')

    if 'urn' in f.getValidValueTypes():
        f.setValidValueTypes([i for i in f.getValidValueTypes() if i != 'urn'])

    # GeoProximitySensor

    n = ndb.getNode('X3DEnvironmentalSensorNode')
    f = n.findField('center')
    n1 = ndb.getNode('GeoProximitySensor')
    if not n1.findField('center'):
        n1.addField(f.copy())

    # GeoViewpoint

    n = ndb.getNode('X3DViewpointNode')
    f = n.findField('orientation')
    n1 = ndb.getNode('GeoViewpoint')
    f1 = n1.findField('orientation')
    if f != f1:
        if not n1.removeField(f1):
            print >> sys.stderr, "CAN'T REMOVE",f1
        if not n1.addField(f):
            print >> sys.stderr,  "CAN'T ADD",f

    n = ndb.getNode('X3DViewpointNode')
    f = n.findField('retainUserOffsets')
    if not n1.findField('retainUserOffsets'):
        n1.addField(f.copy())

    f = n.findField('centerOfRotation')
    if not n1.findField('centerOfRotation'):
        n1.addField(f.copy())

    # MovieTexture

    n = ndb.getNode('X3DSoundSourceNode')
    f = n.findField('pitch')
    n1 = ndb.getNode('MovieTexture')
    if not n1.findField('pitch'):
        n1.addField(f.copy())

    # X3DProductStructureChildNode

    n = ndb.getNode('X3DNode')
    f = n.findField('metadata')
    n1 = ndb.getNode('X3DProductStructureChildNode')
    if not n1.findField('metadata'):
        n1.addField(f.copy())

    # X3DComposedGeometryNode

    n = ndb.getNode('X3DComposedGeometryNode')
    f = n.findField('color')
    if f and f.getValidValueTypes() == ['X3DColorObject']:
        f.setValidValueTypes(['X3DColorNode'])

    # X3DNurbsSurfaceGeometryNode

    n = ndb.getNode('NurbsSet')

    for fn in ('addGeometry', 'removeGeometry', 'geometry'):
        f = n.findField(fn)
        if f and f.getValidValueTypes() == ['NurbsSurface']:
            f.setValidValueTypes([])

    # X3DPickSensorNode

    # LinePickSensor, PointPickSensor, PrimitivePickSensor, VolumePickSensor

    for nn in ('LinePickSensor', 'PointPickSensor', 'PrimitivePickSensor',
               'VolumePickSensor', 'X3DPickSensorNode'):
        n = ndb.getNode(nn)
        f = n.findField('pickTarget')

        if f and ('X3DInlineNode' in f.getValidValueTypes()):
            n.removeField(f)
            f = f.copy()
            valueTypes = f.getValidValueTypes()
            valueTypes.remove('X3DInlineNode')
            f.setValidValueTypes(valueTypes)
            n.addField(f)

    # X3DComposedGeometryNode

    n = ndb.getNode('X3DTexture3DNode')
    f = n.findField('textureProperties')

    n1 = ndb.getNode('ComposedTexture3D')
    f1 = n1.findField('textureProperties')

    if (f and not f1) or (f != f1):
        if not n1.addField(f.copy()):
            print >>sys.stderr, "CAN'T ADD FIELD",f

    # V3.2
    # ParticleSystem
    # MFFloat [] colorKey NULL
    # ->
    # MFFloat [] colorKey []
    n = ndb.getNode('ParticleSystem')
    f = n.findField('colorKey')
    if f.getValue() is None:
        f.setValue('[]')

    # StaticGroup
    # SFVec3f []       bboxCenter 0 0      (-inf,inf)
    # ->
    # SFVec3f []       bboxCenter 0 0 0    (-inf,inf)
    n = ndb.getNode('StaticGroup')
    f = n.findField('bboxCenter')
    if f.getValue() is None:
        f.setValue('0 0 0')

    # Collision, X3DDragSensorNode,
    # X3DPointingDeviceSensorNode, X3DTouchSensorNode
    #
    # SFBool [in,out] enabled
    # ->
    # SFBool [in,out] enabled TRUE
    for nodeName in ('X3DDragSensorNode',
                     'X3DPointingDeviceSensorNode',
                     'X3DTouchSensorNode',
                     'Collision'):
        n = ndb.getNode(nodeName)
        f = n.findField('enabled')
        if f.getValue() is None:
            f.setValue('TRUE')

    # IntegerTrigger
    # SFBool [in,out] integerKey
    # ->
    # SFBool [in,out] integerKey 0 ?
    n = ndb.getNode('IntegerTrigger')
    f = n.findField('integerKey')
    if f.getValue() is None:
        f.setValue('0')


    # Add missing information to the X3D specification that are needed
    # for XML parsing

    # Set containerField

    data = [('children', ('NavigationInfo', 'DirectionalLight',
                          'Transform', 'Shape')),
            ('geometry', ('Sphere', 'Cone', 'Box')),
            ('material', ('Material',)),
            ('appearance', ('Appearance',))
            ]

    for task in data:
        containerFieldName, nodeNameList  = task

        for name in nodeNameList:
            n = ndb.getNode(name)
            n.addField(nodedb.Field('SFString',
                                    nodedb.INITIALIZE_ONLY,
                                    'containerField', '"%s"' % \
                                    containerFieldName, [],
                                    nodedb.Annotations([
                nodedb.Annotation('dontCreate', []) ]), None))

    # Set DEF and USE for all node types
    for n in ndb.getNodeList():
        n.addField(nodedb.Field('SFString',
                                nodedb.INITIALIZE_ONLY,
                                'DEF', '""', [],
                                nodedb.Annotations([
            nodedb.Annotation('isNodeName', []),
            nodedb.Annotation('dontCreate', [])
            ]), None))
        n.addField(nodedb.Field('SFString',
                                nodedb.INITIALIZE_ONLY,
                                'USE', '""', [],
                                nodedb.Annotations([
            nodedb.Annotation('replaceNodeWithReference', []),
            nodedb.Annotation('dontCreate', [])
            ]), None))

    # Add ROUTE node
    _n = nodedb.Node(type='ROUTE')
    #_n.setSuperTypes(['X3DChildNode'])
    _n.setSpecFile('x3d_3.2_fixed.txt')
    _n.setAbstract(False)
    _n.setComponentName('Core')
    # fields
    _n.addField(nodedb.Field('SFNode', nodedb.INITIALIZE_ONLY,
                             'fromNode', 'NULL', [],
                             [ nodedb.Annotation('isReference', []) ], None))
    _n.addField(nodedb.Field('SFString', nodedb.INITIALIZE_ONLY,
                             'fromField', '""', [],
                             [ ], None))
    _n.addField(nodedb.Field('SFNode', nodedb.INITIALIZE_ONLY,
                             'toNode', 'NULL', [],
                             [ nodedb.Annotation('isReference', []) ], None))
    _n.addField(nodedb.Field('SFString', nodedb.INITIALIZE_ONLY,
                             'toField', '""', [],
                             [ ], None))
    ndb.addNode(_n)

    # output ndb to stdout

    ndb.save(sys.stdout)

if __name__ == '__main__':
    main()
