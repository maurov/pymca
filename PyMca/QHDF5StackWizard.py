#/*##########################################################################
# Copyright (C) 2004-2009 European Synchrotron Radiation Facility
#
# This file is part of the PyMCA X-ray Fluorescence Toolkit developed at
# the ESRF by the Beamline Instrumentation Software Support (BLISS) group.
#
# This toolkit is free software; you can redistribute it and/or modify it 
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option) 
# any later version.
#
# PyMCA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# PyMCA; if not, write to the Free Software Foundation, Inc., 59 Temple Place,
# Suite 330, Boston, MA 02111-1307, USA.
#
# PyMCA follows the dual licensing model of Trolltech's Qt and Riverbank's PyQt
# and cannot be used as a free plugin for a non-free program. 
#
# Please contact the ESRF industrial unit (industry@esrf.fr) if this license 
# is a problem for you.
#############################################################################*/
import os
import sys
import PyQt4.QtCore as QtCore
import PyQt4.QtGui as QtGui
import QNexusWidget
import NexusDataSource
import PyMcaDirs
import posixpath

class IntroductionPage(QtGui.QWizardPage):
    def __init__(self, parent):
        QtGui.QWizardPage.__init__(self, parent)
        self.setTitle("HDF5 Stack Selection Wizard")
        text  = "This wizard will help you to select the "
        text += "appropriate dataset(s) belonging to your stack"
        self.setSubTitle(text)

class FileListPage(QtGui.QWizardPage):
    def __init__(self, parent):
        QtGui.QWizardPage.__init__(self, parent)
        self.setTitle("HDF5 Stack File Selection")
        text  = "The files below belong to your stack"
        self.setSubTitle(text)
        self.fileList = []
        self.inputDir = None
        self.mainLayout= QtGui.QVBoxLayout(self)
        listlabel   = QtGui.QLabel(self)
        listlabel.setText("Input File list")
        self._listView = QtGui.QTextEdit(self)
        self._listView.setMaximumHeight(30*listlabel.sizeHint().height())
        self._listView.setReadOnly(True)
        
        self._listButton = QtGui.QPushButton(self)
        self._listButton.setText('Browse')
        self._listButton.setAutoDefault(False)

        self.mainLayout.addWidget(listlabel)
        self.mainLayout.addWidget(self._listView)
        self.mainLayout.addWidget(self._listButton)

        self.connect(self._listButton,
                     QtCore.SIGNAL('clicked()'),
                     self.browseList)

    def setFileList(self, filelist):
        text = ""
        filelist.sort()
        for ffile in filelist:
            text += "%s\n" % ffile
        self.fileList = filelist
        self._listView.setText(text)

    def validatePage(self):
        if not len(self.fileList):
            return False
        return True

    def browseList(self):
        if self.inputDir is None:
            self.inputDir = PyMcaDirs.inputDir
        if not os.path.exists(self.inputDir):
            self.inputDir =  os.getcwd()
        wdir = self.inputDir
        filedialog = QtGui.QFileDialog(self)
        filedialog.setWindowTitle("Open a set of files")
        filedialog.setDirectory(wdir)
        filedialog.setFilters(["HDF5 Files (*.nxs *.h5 *.hdf)",
                               "HDF5 Files (*.h5)",
                               "HDF5 Files (*.hdf)",
                               "HDF5 Files (*.nxs)",
                               "HDF5 Files (*)"])
        filedialog.setModal(1)
        filedialog.setFileMode(filedialog.ExistingFiles)
        ret = filedialog.exec_()
        if  ret == QtGui.QDialog.Accepted:
            filelist0=filedialog.selectedFiles()
        else:
            self.raise_()
            return            
        filelist = []
        for f in filelist0:
            filelist.append(str(f))
        if len(filelist):
            self.setFileList(filelist)
        PyMcaDirs.inputDir = os.path.dirname(filelist[0])
        self.inputDir = os.path.dirname(filelist[0])
        self.raise_()


class StackIndexWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.mainLayout = QtGui.QHBoxLayout(self)
        #self.mainLayout.setMargin(0)
        #self.mainLayout.setSpacing(0)

        self.buttonGroup = QtGui.QButtonGroup(self)
        for text in ["1D data is first dimension", "1D data is last dimension"]:
            rButton = QtGui.QRadioButton(self)
            rButton.setText(text)
            self.mainLayout.addWidget(rButton)
            self.buttonGroup.addButton(rButton)
        rButton.setChecked(True)
        self._stackIndex = -1
        self.connect(self.buttonGroup,
                         QtCore.SIGNAL('buttonPressed(QAbstractButton *)'),
                         self._slot)

    def _slot(self, button):
        if "first" in str(button.text()).lower():
            self._stackIndex =  0
        else:
            self._stackIndex = -1

class DatasetSelectionPage(QtGui.QWizardPage):
    def __init__(self, parent):
        QtGui.QWizardPage.__init__(self, parent)
        self.setTitle("HDF5 Dataset Selection")
        text  = "Double click on the datasets you want to consider "
        text += "and select the role they will play at the end by "
        text += "selecting the appropriate checkbox(es)"
        self.selection = None
        self.setSubTitle(text)
        self.mainLayout = QtGui.QVBoxLayout(self)
        self.nexusWidget = LocalQNexusWidget(self)
        self.nexusWidget.buttons.hide()
        self.mainLayout.addWidget(self.nexusWidget, 1)

        self.stackIndexWidget = StackIndexWidget(self)
        self.mainLayout.addWidget(self.stackIndexWidget, 0)

    def setFileList(self, filelist):
        self.dataSource = NexusDataSource.NexusDataSource(filelist[0])
        self.nexusWidget.setDataSource(self.dataSource)
        phynxFile = self.dataSource._sourceObjectList[0]
        keys = phynxFile.keys()
        if len(keys) != 1:
            return
        
        #check if it is an NXentry
        entry = phynxFile[keys[0]] 
        attr = entry.attrs.get('NX_class',None)
        if attr is None:
            return
        if attr != 'NXentry':
            return

        #check if there is only one NXdata
        nxDataList = []
        for key in entry.keys():
            attr = entry[key].attrs.get('NX_class', None)
            if attr in ['NXdata']:
                nxDataList.append(key)
        if len(nxDataList) != 1:
            return
        nxData = entry[nxDataList[0]]

        #try to get the signals
        signalList = []
        for key in nxData.keys():
            if 'signal' in nxData[key].attrs.keys():
                if int(nxData[key].attrs['signal']) == 1:
                    signalList.append(key)

        if not len(signalList):
            return

        ddict = {}
        ddict['counters'] = []
        ddict['aliases']  = []
        
        for signal in signalList:
            path = posixpath.join("/",nxDataList[0], signal)
            ddict['counters'].append(path)
            ddict['aliases'].append(posixpath.basename(signal))
        self.nexusWidget.setWidgetConfiguration(ddict)
        self.nexusWidget.cntTable.setCounterSelection({'y':[0]})

    def validatePage(self):
        cntSelection = self.nexusWidget.cntTable.getCounterSelection()
        cntlist = cntSelection['cntlist']
        if not len(cntlist):
            text = "No dataset selection"
            self.showMessage(text)
            return False
        if not len(cntSelection['y']):
            text = "No dataset selected as y"
            self.showMessage(text)
            return False
        selection = {}
        selection['x'] = []
        selection['y'] = []
        selection['m'] = []
        selection['index'] = self.stackIndexWidget._stackIndex
        for key in ['x', 'y', 'm']:
            if len(cntSelection[key]):
                for idx in cntSelection[key]:
                    selection[key].append(cntlist[idx])              
        self.selection = selection
        return True

    def showMessage(self, text):
        msg = QtGui.QMessageBox(self)
        msg.setIcon(QtGui.QMessageBox.Information)
        msg.setText(text)
        msg.exec_()            
        
class ShapePage(QtGui.QWizardPage):
    def __init__(self, parent):
        QtGui.QWizardPage.__init__(self, parent)
        self.setTitle("HDF5 Map Shape Selection")
        text  = "Adjust the shape of your map if necessary"
        self.setSubTitle(text)

class LocalQNexusWidget(QNexusWidget.QNexusWidget):
    def showInfoWidget(self, filename, name, dset=False):
        w = QNexusWidget.QNexusWidget.showInfoWidget(self, filename, name, dset)
        w.hide()
        w.setWindowModality(QtCore.Qt.ApplicationModal)
        w.show()

class QHDF5StackWizard(QtGui.QWizard):
    def __init__(self, parent=None):
        QtGui.QWizard.__init__(self, parent)
        self.setWindowTitle("HDF5 Stack Wizard")
        #self._introduction = self.createIntroductionPage()
        self._fileList     = self.createFileListPage()
        self._datasetSelection = self.createDatasetSelectionPage()
        #self._shape        = self.createShapePage()
        #self.addPage(self._introduction)
        self.addPage(self._fileList)
        self.addPage(self._datasetSelection)
        #self.addPage(self._shape)
        #self.connect(QtCore.SIGNAL("currentIdChanged(int"),
        #             currentChanged)

    def sizeHint(self):
        width = QtGui.QWizard.sizeHint(self).width()
        height = QtGui.QWizard.sizeHint(self).height()
        return QtCore.QSize(width, int(1.5 * height))

    def createIntroductionPage(self):
        return IntroductionPage(self)

    def setFileList(self, filelist):
        self._fileList.setFileList(filelist)
        
    def createFileListPage(self):
        return FileListPage(self)

    def createDatasetSelectionPage(self):
        return DatasetSelectionPage(self)
    
    def createShapePage(self):
        return ShapePage(self)

    def initializePage(self, value):
        if value == 1:
            #dataset page
            self._datasetSelection.setFileList(self._fileList.fileList)

    def getParameters(self):
        return self._fileList.fileList, self._datasetSelection.selection
    
if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    w = QHDF5StackWizard()
    ret = w.exec_()
    if ret == QtGui.QDialog.Accepted:
        print w.getParameters()
    #QtCore.QObject.connect(w, QtCore.SIGNAL("addSelection"),     addSelection)
    #QtCore.QObject.connect(w, QtCore.SIGNAL("removeSelection"),  removeSelection)
    #QtCore.QObject.connect(w, QtCore.SIGNAL("replaceSelection"), replaceSelection)
