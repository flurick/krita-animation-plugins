doc_a = Krita.activeDocument()
start_time = doc_a.playBackStartTime()
time = doc_a.currentTime()
end_time = doc_a.playBackEndTime()

Krita.instance().action('set_end_time').trigger()

old_views = Krita.views()
Krita.instance().action('create_copy').trigger()
#wait for copy to be done
while old_views == Krita.views():
    sleep(0.1)

#print(time, end_time)
doc_b = Krita.activeDocument()
doc_b.setFullClipRangeStartTime(time)
doc_b.setFullClipRangeEndTime(end_time)
doc_b.setCurrentTime(time)

