#!/usr/bin/env python

# ndb2cpp.py -- X3D Type Hierarchy to C++ Data Structure Converter
#
# Authors: Dmitri Rubinstein <rubinstein@cs.uni-saarland.de>,
#          Boris Broenner <borisbroenner@googlemail.com>
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
import StringIO
import nodedb

##########################################################################
# CPPExporter (C++ exporter)
##########################################################################

def cquote(s):
    """ simple hack """
    r = '"'
    for c in s:
        if c == '\n':
            r += '\\n'
        elif c == '\t':
            r += '\\t'
        elif c == '\r':
            r += '\\r'
        elif c == '\b':
            r += '\\b'
        elif c == '\f':
            r += '\\f'
        elif c == '\\':
            r += '\\\\'
        elif c == '"':
            r += '\\"'
        else:
            # check for printable char ?
            r += c
    r += '"'
    return r

def cquote_list(l):
    return '{' + ', '.join(map(cquote, l)) + '}'

class TypedRepr(object):

    def __init__(self, valueType):
        self.valueType = valueType

    def __call__(self, value):
        if isinstance(value, list) or isinstance(value, tuple):
            r = ', '.join(map(repr, value))
        else:
            r = repr(value)
        return '%s(%s)' % (self.valueType, r)

def reprRotation(value):
    return 'SFRotation::ValueType().setAxisAngle(Vec3f(%s, %s, %s), %s)' % \
           (repr(value[0]), repr(value[1]), repr(value[2]), repr(value[3]))

def reprBool(value):
    if value:
        return 'true'
    else:
        return 'false'

def reprImage(value):
    # TODO
    return 'Image(%i,%i,PixelFormat::RGB_24)' % (value[0],value[1])

def reprNode(value):
    if isinstance(value, nodedb.NullNode):
        return 'PointerTraits<Node>::Ptr(0)'
    raise ValueError('Unsupported value %s of type SFNode' % \
                     (repr(value),))

SINGLE_VALUE_CONVERTERS = {
    'SFInt32' : repr,
    'MFInt32' : repr,
    'SFFloat' : repr,
    'MFFloat' : repr,
    'SFDouble' : repr,
    'MFDouble' : repr,
    'SFTime' : repr,
    'MFTime' : repr,
    'SFVec2f' : TypedRepr('SFVec2f::ValueType'),
    'MFVec2f' : TypedRepr('MFVec2f::Value1Type'),
    'SFVec3f' : TypedRepr('SFVec3f::ValueType'),
    'MFVec3f' : TypedRepr('MFVec3f::Value1Type'),
    'SFVec4f' : TypedRepr('SFVec4f::ValueType'),
    'MFVec4f' : TypedRepr('MFVec4f::Value1Type'),
    'SFMatrix4f' : TypedRepr('SFMatrix4f::ValueType'),
    'MFMatrix4f' : TypedRepr('MFMatrix4f::Value1Type'),
    'SFVec2d' : TypedRepr('SFVec2d::ValueType'),
    'MFVec2d' : TypedRepr('MFVec2d::Value1Type'),
    'SFVec3d' : TypedRepr('SFVec3d::ValueType'),
    'MFVec3d' : TypedRepr('MFVec3d::Value1Type'),
    'SFVec4d' : TypedRepr('SFVec4d::ValueType'),
    'MFVec4d' : TypedRepr('MFVec4d::Value1Type'),
    'SFMatrix4d' : TypedRepr('SFMatrix4d::ValueType'),
    'MFMatrix4d' : TypedRepr('MFMatrix4d::Value1Type'),
    'SFColor' : TypedRepr('SFColor::ValueType'),
    'MFColor' : TypedRepr('MFColor::Value1Type'),
    'SFColorRGBA' : TypedRepr('SFColorRGBA::ValueType'),
    'MFColorRGBA' : TypedRepr('MFColorRGBA::Value1Type'),
    'SFRotation' : reprRotation,
    'MFRotation' : reprRotation,
    'SFBool' : reprBool,
    'MFBool' : reprBool,
    'SFString' : cquote,
    'MFString' : cquote,
    'SFImage' : reprImage,
    'MFImage' : reprImage,
    'SFNode' : reprNode,
    'MFNode' : reprNode
    }

def convertSingleValue(fieldType, value):
    global SINGLE_VALUE_CONVERTERS
    conv = SINGLE_VALUE_CONVERTERS.get(fieldType)
    if conv is None:
        raise ValueError('Missing converter for value %s with type %s' % \
                         (repr(value), fieldType))
    return conv(value)

class CPPExporter:

    def __init__(self, nodeDB, nodes=None):
        self.nodeDB = nodeDB
        self.nodes = nodes
        self.nodeList = None
        # C/C++ initialization variables buffer
        self._cVarBuf = None
        # C-Variable counter
        self._cVarCount = 0
        # variable generation buffer
        self._varBuf = None
        # main generation buffer
        self._mainBuf = None
        # default value initialization variables
        self._initVars = None
        # conversion cache
        self._convertCache = {}

    def _getCVarName(self):
        name = '_cvar_%i' % self._cVarCount
        self._cVarCount+=1
        return name

    def convertValue(self, fieldType, value, varName):
        if fieldType.startswith('SF'):
            return convertSingleValue(fieldType, value)

        assert fieldType.startswith('MF')

        if len(value) == 0:
            return ''

        if len(value) == 1:
            return '%s::ContainerType(1, %s)' % \
                   (fieldType, convertSingleValue(fieldType, value[0]))

        cvarName = self._getCVarName()
        if fieldType == 'MFString':
            cvarType = 'const char *'
        else:
            cvarType = '%s::Value1Type' % fieldType

        cValue = map(lambda v: convertSingleValue(fieldType, v), value)
        cValue = ', '.join(cValue)

        print >>self._cVarBuf, 'static %s const %s[] = {%s};' % \
              (cvarType, cvarName, cValue)

        return '%s::ContainerType(%s, %s+%i)' % \
               (fieldType, cvarName, cvarName, len(value))

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

    def getInitVarName(self, field):
        """returns name of the default value initialization variable,
           or None if no available"""
        # Construct dictionary key

        parsedValue = field.getParsedValue()
        if parsedValue is None:
            return None
        key = str(field.getType())+' '+repr(parsedValue)

        varName = self._initVars.get(key)
        if varName is not None:
            return varName

        # Create new variable name
        varName = 'fieldInitVar'+str(len(self._initVars))
        self._initVars[key] = varName

        initializerType = None
        if field.getType().startswith('MF'):
            if len(parsedValue) == 0:
                initializerType = 'EmptyMFieldInitializer'
                valuePattern = ''
            else:
                initializerType = 'SimpleInitializer'
                valuePattern = '(%s)'
        else:
            initializerType = 'SimpleInitializer'
            valuePattern = '(%s)'

        if valuePattern:
            value = valuePattern % self.convertValue( \
                field.getType(), parsedValue, varName)
        else:
            value = ''

        print >>self._varBuf, 'static const %s<%s> %s%s;' %   \
              (initializerType, field.getType(), varName, value)
        return varName

    # returns a tuple (formatstr, annotation values)
    #     formatstr is the string to be appended to the field definition format string
    def genFieldAnnotations(self, node, field):

        f_encodingId = "-1"
        f_isReference = "false"
        f_isContainment = "false"
        f_isMixedContent = "false"
        f_isResource = "false"
        f_isEnum = "false"
        f_dontCreate = "false"
        f_isNodeName = "false"
        f_replaceNodeWithReference = "false"

        f_annot = field.getAnnotations()

        curann = f_annot.getAnnotation("encodingId")
        if curann and len(curann.getValueList()) > 0:
             f_encodingId = curann.getValueList()[0]

        if f_annot.getAnnotation("isReference"):
            f_isReference = "true"
        if f_annot.getAnnotation("isContainment"):
            f_isContainment = "true"
        if f_annot.getAnnotation("isMixedContent"):
            f_isMixedContent = "true"
        if f_annot.getAnnotation("isResource"):
            f_isResource = "true"
        if f_annot.getAnnotation("enum"):
            f_isEnum = "true"
        if f_annot.getAnnotation("dontCreate"):
            f_dontCreate = "true"
        if f_annot.getAnnotation("isNodeName"):
            f_isNodeName = "true"
        if f_annot.getAnnotation("replaceNodeWithReference"):
            f_replaceNodeWithReference = "true"

        fmtStr = ", %s, %s, %s, %s, %s, %s, %s, %s, %s"
        values = (f_encodingId, f_isReference, f_isContainment,
                  f_isMixedContent, f_isResource, f_isEnum, f_dontCreate,
                  f_isNodeName, f_replaceNodeWithReference)

        return (fmtStr, values)

    # generates the variable names for valid value types used by enums and valid value types themselves
    def genValidValueTypeNames(self, node, field):

        validValueTypesVar = '%s_%s_field_vvt' % \
                                   (node.getType(), field.getName())
        validValueTypesSizeVar = validValueTypesVar + '_size'

        return (validValueTypesVar, validValueTypesSizeVar)

    # returns the string containing the type definitions
    def genValidValueTypedefs(self, node, field):

        validValueTypeDefs = []
        validValueTypes = field.getValidValueTypes()
        n_validValueTypesVar, n_validValueTypesSizeVar = self.genValidValueTypeNames(node, field)

        val = cquote_list(validValueTypes)
        numValidValueTypes = len(validValueTypes)

        validValueTypeDefs.append(
            'const char * %s[] = %s;' % (n_validValueTypesVar,val)
            )
        validValueTypeDefs.append(
            'const size_t %s = %i;' % (n_validValueTypesSizeVar,
                                       numValidValueTypes)
            )

        return validValueTypeDefs

    # returns  the string containing the definitions for the enumeration
    def genFieldEnumAnnotation(self, node, field):

        enumAnnot = field.getAnnotations().getAnnotation('enum')
        assert enumAnnot

        validValueTypeDefs = []
        n_validValueTypesVar, n_validValueTypesSizeVar = self.genValidValueTypeNames(node, field)

        # enum's key is the value of the field,
        # enum's value is the symbolic name of the value
        validValueTypeDefs.append( '// Enum annotation of field %s.%s' % \
              (node.getType(), field.getName()))

        enumVals = '{'
        comma = ''
        for v in enumAnnot.getValueList():
            enumVals += comma + '\"' + v + '\"'
            comma = ','
        enumVals += '}'

        numVals = len(enumAnnot.getValueList())

        validValueTypeDefs.append(
            'const char * %s[] = %s;' % (n_validValueTypesVar, enumVals)
            )
        validValueTypeDefs.append(
            'const size_t %s = %i;' % (n_validValueTypesSizeVar, numVals)
            )

        return validValueTypeDefs

    def genFields(self, node):

        #fields = node.getFields()
        fields = [f for f in node.getFields() if node in f.getDeclarationNodes()]
        flen = len(fields)

        fieldsDefRef = '0'

        if flen:
            
            validValueTypesDefs = []
            fieldDefs = []

            for i in xrange(0, flen):
                field = fields[i]

                f_type = cquote(field.getType())
                f_accessType = field.getAccessTypeConst()
                f_name = cquote(field.getName())

                value = field.getValue()
                if value is not None:
                    f_value = cquote(value)
                else:
                    f_value = '0'

                initVarName = self.getInitVarName(field)
                if initVarName is not None:
                    f_parsedValue = '&'+initVarName
                else:
                    f_parsedValue = '0'


                # valid value typedefs and enums
                n_validValueTypesVar, n_validValueTypesSizeVar = self.genValidValueTypeNames(node, field)

                enumAnnot = field.getAnnotations().getAnnotation('enum')

                if len(field.getValidValueTypes()) > 0:
                    assert enumAnnot is None
                    validValueTypesDefs.extend(self.genValidValueTypedefs(node, field))

                elif enumAnnot:
                    validValueTypesDefs.extend(self.genFieldEnumAnnotation(node, field))

                else:
                    n_validValueTypesVar = 0
                    n_validValueTypesSizeVar = 0

                # other annotations
                annotFmtStr, annotValues = self.genFieldAnnotations(node, field)

                # field definition string
                fieldAttrs = (f_type, f_accessType, f_name, f_value, f_parsedValue,
                     n_validValueTypesVar, n_validValueTypesSizeVar) + annotValues

                s = '   '
                s+='{%s, %s, %s, %s, %s, %s, %s'
                s+= annotFmtStr
                s+= '}'
                s = s % fieldAttrs

                if i != flen-1:
                    s+=','

                fieldDefs.append(s)

            # output field definitions

            for d in validValueTypesDefs:
                print >>self._mainBuf, d

            fieldsDefRef = '%s_fields' % node.getType()
            print >>self._mainBuf, 'const FieldDef %s[] =\n{' % fieldsDefRef

            for d in fieldDefs:
                print >>self._mainBuf, d

            print >>self._mainBuf, '};'

        fieldsSizeVar = '%s_fields_size' % node.getType()

        print >>self._mainBuf, 'const size_t %s = %i;' % (fieldsSizeVar, flen)
        print >>self._mainBuf

        return [fieldsDefRef, fieldsSizeVar, flen]

    def export(self, out):
        # initialize output buffers
        self._cVarBuf = StringIO.StringIO()
        self._varBuf = StringIO.StringIO()
        self._mainBuf = StringIO.StringIO()

        # initialize default value initialization variables
        self._initVars = {}
        self._cVarCount = 0

        self._computeNodeList()

        nodeDefs = []

        for node in self.nodeList:
            #derivedNodes = [n for n in node.getDerivedNodes() if n in self.nodeList]
            if node.getAttribute("externalDefinition"):
                continue

            nodeType = node.getType()

            print >>self._mainBuf
            print >>self._mainBuf, "// ---- %s ----" % (nodeType,)
            print >>self._mainBuf

            fieldsDefRef, fieldsSizeVar, numFields = self.genFields(node)

            superTypes = node.getSuperTypes()

            n_superTypesVar = '%s_superTypes' % nodeType
            n_superTypesSizeVar = '%s_size' % n_superTypesVar
            
            if len(superTypes):
                val = cquote_list(superTypes)
                n_superTypes = n_superTypesVar
                n_numSuperTypes = len(superTypes)

                print >>self._mainBuf, 'const char * %s[] = %s;' % \
                      (n_superTypesVar, val)
                print >>self._mainBuf, 'const size_t %s = %i;' % \
                      (n_superTypesSizeVar, n_numSuperTypes)

            else:
                n_superTypes = '0'
                n_numSuperTypes = 0
                print >>self._mainBuf, 'const size_t %s = 0;' % \
                      n_superTypesSizeVar

            n_type = cquote(nodeType)

            if node.isAbstract():
                n_abstract = 'true'
            else:
                n_abstract = 'false'
            n_componentName = cquote(node.getComponentName())

            #nodeVar = '%s_node' % nodeType

            n_auxTypeName = node.getAttribute("auxTypeName")
            if n_auxTypeName is None:
                n_auxTypeName = ""
            n_auxTypeName = cquote(n_auxTypeName)

            n_encodingId = node.getAttribute("encodingId")
            if n_encodingId is None:
                n_encodingId = -1
            else:
                n_encodingId = int(n_encodingId)


            nodeDefs.append((n_type, n_superTypes, n_superTypesSizeVar,
                             fieldsDefRef, fieldsSizeVar, # or numFields ?
                             n_abstract, n_componentName,
                             n_auxTypeName, n_encodingId))


            #pc = ';'.join([n.getType() for n in derivedNodes])
            #print '%s -> { %s }' % (node.getType(), pc)


        print >>self._mainBuf, 'const NodeDef nodeDefs[] =\n{'

        ndlen = len(nodeDefs)

        for i in xrange(0, ndlen):
            nodeDef = nodeDefs[i]

            if i != ndlen-1:
                s=','
            else:
                s=''

            print >>self._mainBuf, ('    {%s, %s, %s, %s, %s, %s, %s, %s, %i}' % \
                                    nodeDef)+s

        print >>self._mainBuf, '};'

        print >>self._mainBuf, 'const size_t nodeDefs_size = %i;' % \
              len(nodeDefs)

        # Generate file

        # Header

        print >>out, "// Generated with ndb2cpp.py"
        print >>out
        print >>out, "#include <RTSG/Base/Fields/Fields.hpp>"
        print >>out, "#include <RTSG/Base/DataModel/StaticDefs.hpp>"
        print >>out
        print >>out, "#ifdef SPEC_NAMESPACE"
        print >>out, "namespace SPEC_NAMESPACE {"
        print >>out, "#endif"
        print >>out
        print >>out, "using namespace RTSG;"

        # Variables

        out.write(self._cVarBuf.getvalue())
        out.write(self._varBuf.getvalue())

        # Body

        out.write(self._mainBuf.getvalue())

        # Footer
        print >>out
        print >>out, "#ifdef SPEC_NAMESPACE"
        print >>out, "} // namespace SPEC_NAMESPACE"
        print >>out, "#endif"

        # Deinitialization
        self._cVarBuf.close()
        self._cVarBuf = None
        self._varBuf.close()
        self._varBuf = None
        self._mainBuf.close()
        self._mainBuf = None
        self._initVars = None


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

    de = CPPExporter(nodeDB, nodes)
    de.export(sys.stdout)

if __name__ == '__main__':
    main()
