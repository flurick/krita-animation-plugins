from krita import *

class AnimationView(DockWidget):
    
    def __init__(self):
        super().__init__()
        self.buffer = [] #[QPixmap]
        self.frameIndex = 1

        self.setWindowTitle("Animation View")

        self.timer = QTimer()
        self.timer.timeout.connect(self.next_frame)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        # Mini timeline
        self.row = QHBoxLayout()
        self.row.setAlignment(Qt.AlignBottom)
        #
        self.playButtonGroup = QButtonGroup()
        self.playButtonGroup.setExclusive(True)
        #
        self.playButton = QPushButton("▶️")
        self.playButton.setCheckable(True)
        self.playButton.setChecked(False)
        self.playButton.toggled.connect(self.toggle_play)
        self.playButton.setMaximumSize(24,24)
        self.row.addWidget(self.playButton)
        #
        self.timecode = QLabel()
        self.timecode.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.row.addWidget(self.timecode)
        #
        self.reloadButton = QPushButton("🔄")
        self.reloadButton.setToolTip("Reload all frames")
        self.reloadButton.setMaximumSize(24,24)
        self.reloadButton.setCheckable(True)
        self.reloadButton.setChecked(False)
        self.reloadButton.clicked.connect(self.getAllThumbnails)
        self.row.addWidget(self.reloadButton)
        #
        layout.addLayout(self.row)

        self.setWidget(widget)

    def refresh_thumbnail(self):

        #pad out buffer if needed
        doc = Application.activeDocument()
        if len(self.buffer) < self.frameIndex+1:

            bookmark = doc.currentTime()
            for i in range(len(self.buffer), doc.fullClipRangeEndTime()+1):
                #doc.setCurrentTime(i)
                #thumbnail = doc.thumbnail(256,256)
                thumbnail = self.getFrame(i) #less breaking?
                pixmap = QPixmap.fromImage(thumbnail)
                self.buffer.append(pixmap)
                QApplication.processEvents() #allow krita to update the ui
            doc.setCurrentTime(bookmark)
            print("paaaaaaaaded")

        #save thumbnail
        if self.frameIndex == doc.currentTime():
            thumbnail = self.getFrame(doc.currentTime())
            pixmap = QPixmap.fromImage(thumbnail)
            if len(self.buffer) > self.frameIndex:
                self.buffer[self.frameIndex] = pixmap

        #show thumbnail
        if len(self.buffer) > self.frameIndex:
            if self.buffer[self.frameIndex] is not None:
                self.label.setPixmap(self.buffer[self.frameIndex])

    def getFrame(self, frame):
        
        doc = Application.activeDocument()
        #pixelData = doc.rootNode().getPixelDataAtTime(0, 0, doc.width(), doc.height(), frame)
        #image = QImage(pixelData, doc.width(), doc.height(), QImage.Format.Format_ARGB32) #Not for groups :(
        doc.setCurrentTime(frame)
        image = doc.thumbnail(256,256)
        return image

    def getAllThumbnails(self):
        doc = Application.activeDocument()
        a = doc.fullClipRangeStartTime()
        b = doc.fullClipRangeEndTime()

        #fixme: onionskin should probably be temporarily disabled for the thumbnails

        bookmark = doc.currentTime()
        self.buffer.clear()
        shouldPlay = self.playButton.isChecked()
        self.playButton.setChecked(False)
        self.playButton.setDisabled(True)

        for i in range(a, b+1):
            #doc.setCurrentTime(i)
            self.buffer.append( QPixmap.fromImage(self.getFrame(i)) )

            self.timecode.setText(f"Loading: {i}/{b}")
            
            QApplication.processEvents() #allow krita to update the ui
            if not self.reloadButton.isChecked(): #stop if play button is off again
                break
        self.reloadButton.setChecked(False)

        #reset state to before reloading frames
        doc.setCurrentTime(bookmark)
        self.playButton.setDisabled(False)
        if shouldPlay:
            self.playButton.setChecked(True)
                

    def canvasChanged(self, canvas):
        pass

            
    def next_frame(self):
        doc = Application.activeDocument()
        if doc:

            self.frameIndex += 1
            if self.frameIndex > doc.fullClipRangeEndTime():
                self.frameIndex = doc.fullClipRangeStartTime()
                                
            self.timecode.setText(f"{self.frameIndex}/{len(self.buffer)}")

            self.refresh_thumbnail()

    def toggle_play(self):
        if self.playButton.isChecked():
            #self.getAllThumbnails()
            self.timer.start( int(1000/Application.activeDocument().framesPerSecond()) )
            self.playButton.setText("⏸️")
        else:
            self.timer.stop()
            self.playButton.setText("▶️")

Krita.instance().addDockWidgetFactory( DockWidgetFactory("AnimationView", DockWidgetFactoryBase.DockRight, AnimationView))
