from krita import *

class blackspace(Extension):

    def __init__(self, parent):
        super().__init__(parent)



    def setup(self):
        appNotifier = Application.instance().notifier()
        appNotifier.setActive(True)
        appNotifier.windowCreated.connect(self.applyStyle)
        #appNotifier.imageCreated.connect(self.applyDocTemplate)


    def applyDocTemplate(self):
        Application.activeDocument().setFullClipRangeStartTime(1)
        #Application.writeSetting("useLayerSelectionCheckbox", "true") #maybe somethinglike this?


    def createActions(self, window):
        action = window.createAction("blackspace", "Apply BlackSpace")
        action.triggered.connect(self.applyStyle)


    def applyStyle(self):
        
        #slim bottom dock
        Application.activeWindow().qwindow().setCorner(3,2) #bottom right corner
        Application.activeWindow().qwindow().setCorner(2,1) #bottom left corner
        
        #new empty style
        css = ""
        
        #black dock spacing
        css += "QMainWindow::separator{width:1; background:palette(shadow);}"

        #black dock tabs
        #css += "\
        #QTabBar{background:palette(shadow); color:white;}\
        #QTabBar::tab{padding:1ex; height:24;}\
        #QTabBar::tab:selected{background:palette(window);}"
        
        #outline floating docks
        #css += "\
        #QDockWidget{background:palette(shadow); border:8 solid;}\
        #QDockWidget:window KSqueezedTextLabel {background:palette(shadow); color:white;}\
        #QDockWidget:window > QWidget {background:palette(window);}"
        
        #apply the css style
        Application.activeWindow().qwindow().setStyleSheet(css)

        #give right dock corner
        Application.activeWindow().qwindow().setCorner(3,2)

        for docker in Application.dockers():
            #avoid preset zoom
            if docker.objectName() == "PresetDocker":
                docker.setMinimumSize(12, 125) 
            #avoid color wheel zoom
            if docker.objectName() == "ColorSelectorNg":
                docker.setMaximumSize(999, 228)
            #slim tool box
            if docker.objectName() == "ToolBox":
                docker.setMinimumSize(12,12)
        
        #use default titlebars
        for d in Krita.instance().dockers():
            d.setTitleBarWidget(None)
            #show animation control buttons inside the timeline
            if d.objectName() == "TimelineDocker":
                d.setStyleSheet("\
                    KisAnimTimelineDockerTitlebar > QLabel { color: transparent; }\
                    KisAnimTimelineFramesView { margin-top: 32; } \
                ")
                for item in d.findChildren(QWidget):
                    if item.metaObject().className() == "KisAnimTimelineDockerTitlebar":
                        item.setVisible(True) #show animaton control buttons


Krita.instance().addExtension(blackspace(Krita.instance())) 
