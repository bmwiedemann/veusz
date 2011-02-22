#    Copyright (C) 2011 Jeremy S. Sanders
#    Email: Jeremy Sanders <jeremy@jeremysanders.net>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
###############################################################################

"""A Qt data model show a tree of Python nodes."""

import bisect
import qtall as qt4

class TMNode(object):
    """Object to represent nodes in TreeModel.

    Each node has a tuple of data items, a parent node and a list of
    child nodes.
    """

    def __init__(self, data, parent):
        self.data = data
        self.parent = parent
        self.childnodes = []

    def getTooltip(self, column):
        """Return tooltip for column, if any."""
        return qt4.QVariant()

    def doPrint(self, indent=0):
        """Print out tree for debugging."""
        print " "*indent, self.data
        for c in self.childnodes:
            c.doPrint(indent=indent+1)

    def deleteFromParent(self):
        """Delete this node from its parent."""
        del self.parent.childnodes[self.parent.childnodes.index(self)]

    def getData(self, idx):
        """Get data with index given."""
        try:
            return qt4.QVariant(self.data[idx])
        except:
            return qt4.QVariant()

    def childWithData1(self, d):
        """Get child node with 1st column data d."""
        for c in self.childnodes:
            if c.data[0] == d:
                return c
        return None

    def insertChildSorted(self, newchild):
        """Insert child alphabetically using data d."""
        cdata = [c.data for c in self.childnodes]
        idx = bisect.bisect_left(cdata, newchild.data)
        newchild.parent = self
        self.childnodes.insert(idx, newchild)

    def cloneTo(self, newroot):
        """Make a clone of self at the root given."""
        return self.__class__(self.data, newroot)

class TreeModel(qt4.QAbstractItemModel):
    """A Qt model for storing Python nodes in a tree.

    The nodes are TMNode objects above."""

    def __init__(self, rootdata, *args):
        """Construct the model.
        rootdata is a tuple of data for the root node - it should have
        the same number of columns as other datasets."""

        qt4.QAbstractItemModel.__init__(self, *args)
        self.root = TMNode(rootdata, None)

    def columnCount(self, parent):
        return len(self.root.data)

    def data(self, index, role):
        if index.isValid():
            if role == qt4.Qt.DisplayRole:
                item = index.internalPointer()
                return item.getData(index.column())
            elif role == qt4.Qt.ToolTipRole:
                item = index.internalPointer()
                return item.getTooltip(index.column())

        return qt4.QVariant()

    def flags(self, index):
        if not index.isValid():
            return qt4.Qt.NoItemFlags
        return qt4.Qt.ItemIsEnabled | qt4.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if orientation == qt4.Qt.Horizontal and role == qt4.Qt.DisplayRole:
            return self.root.getData(section)
        return qt4.QVariant()

    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return qt4.QModelIndex()

        if not parent.isValid():
            parentitem = self.root
        else:
            parentitem = parent.internalPointer()

        childitem = parentitem.childnodes[row]
        if childitem:
            return self.createIndex(row, column, childitem)
        return qt4.QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return qt4.QModelIndex()

        childitem = index.internalPointer()
        parentitem = childitem.parent

        if parentitem is self.root:
            return qt4.QModelIndex()

        parentrow = parentitem.parent.childnodes.index(parentitem)
        return self.createIndex(parentrow, 0, parentitem)

    def rowCount(self, parent):
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parentitem = self.root
        else:
            parentitem = parent.internalPointer()

        return len(parentitem.childnodes)

    def syncTree(self, newroot):
        """Syncronise the displayed tree with the given tree new."""

        def _getdata(theroot):
            """Get a set of child node data and a mapping of data to node."""
            lookup = {}
            data = []
            for c in theroot.childnodes:
                lookup[c.data] = c
                data.append(c.data)
            return lookup, set(data)

        def syncbranch(parentidx, root, newroot):
            """Do synchronisation of branch given for nodes."""

            # FIXME: this doesn't work if there are duplicates
            # use LCS - longest common sequence instead
            clookup, cdata = _getdata(root)
            nlookup, ndata = _getdata(newroot)
            if not cdata and not ndata:
                return

            common = cdata & ndata

            # items to remove (no longer in new data)
            todelete = cdata - common

            # sorted list to add (added to new data)
            toadd = list(ndata - common)
            toadd.sort()

            # iterate over entries, adding and deleting as necessary
            i = 0
            c = root.childnodes

            while i < len(newroot.childnodes) or i < len(c):
                try:
                    k = c[i].data
                except IndexError:
                    k = None
                # one to be deleted
                if k in todelete:
                    todelete.remove(k)
                    #print "deleting row", i, c[i].data
                    self.beginRemoveRows(parentidx, i, i)
                    del c[i]
                    self.endRemoveRows()
                    continue
                # one to insert
                if toadd and (k > toadd[0] or k is None):
                    #print "adding row", i, toadd[0]
                    self.beginInsertRows(parentidx, i, i)
                    c.insert(i, nlookup[toadd[0]].cloneTo(root))
                    self.endInsertRows()
                    del toadd[0]
                
                # now recurse to add any subnodes
                myindex = self.index(i, 0, parentidx)
                syncbranch(myindex, c[i], newroot.childnodes[i])
                i += 1
        
        syncbranch( qt4.QModelIndex(), self.root, newroot )