

import pyaudio
import pyttsx
from threading import Thread
import wave

LARGEST_REGION = 0
BOUNDING_BOX = 1


class ProtocolOperations():
    def __init__(self, canvas, EDFTS):
        self._canvas = canvas
        self._plugin_canvas_artifacts = []
        self._EDFTS = EDFTS
        self._feed_text = self._canvas.create_text(1, 1, anchor="nw", fill="white")
        self._plugin_canvas_artifacts.append(self._feed_text)
        self._added_columns = ()
        self._added_column_widths = []

        self._tts_engine = pyttsx.init()
        
        self._tts_engine.setProperty("rate", 150)
        self._tts_engine.startLoop(False)


    def calculate_target_centroid(self, target, mode=LARGEST_REGION):
        coords = ()
        target_name = "_internal_name" + ":" + target["regions"][0]["_internal_name"]
        
        if mode == LARGEST_REGION:
            regions = self._canvas.find_withtag(target_name)
            largest_region = None

            
            for region in regions:
                if largest_region is None:
                    largest_region = region
                elif self._area_bbox(largest_region) < self._area_bbox(region):
                    largest_region = region

            coords = self._canvas.coords(largest_region)

        elif mode == BOUNDING_BOX:
            coords = self._canvas.bbox(target_name)

        x = coords[::2]
        y = coords[1::2]
        return (sum(x) / len(x), sum(y) / len(x))

  
    def _area_bbox(self, region):
        coords = self._canvas.bbox(region)
        width = coords[2] - coords[0]
        height = coords[3] - coords[1]
        return (width * height)


    def add_shot_list_columns(self, new_columns, widths):
        self._added_columns += new_columns
        if len(self._added_column_widths) == 0:
            self._added_column_widths = widths
        else:
            self._added_column_widths += widths 

        self._EDFTS.add_shot_list_columns(new_columns)
        self._EDFTS.configure_default_shot_list_columns()
        self._EDFTS.configure_shot_list_columns(self._added_columns,
            self._added_column_widths)               


    def append_shot_item_values(self, item, values):
        self._EDFTS.append_shot_list_column_data(item, values)

    def destroy(self):

        if hasattr(self._tts_engine, "_inLoop") and self._tts_engine._inLoop:
            self._tts_engine.endLoop()
        elif not hasattr(self._tts_engine, "_inLoop"):
            self._tts_engine.endLoop()
        self.clear_canvas()
        self.clear_protocol_shot_list_columns()

    def clear_shots(self):
        self._EDFTS.clear_shots()

 
    def say(self, message):
     
        self._say_thread = Thread(target=self._say, args=(message,),
                name="say_thread")
        self._say_thread.start()  
    
    def _say(self, *args):
        self._tts_engine.say(args[0])
        self._tts_engine.iterate()


    def show_text_on_feed(self, message):
        self._canvas.itemconfig(self._feed_text, text=message)

  
    def clear_canvas(self):
        for artifact in self._plugin_canvas_artifacts:
            self._canvas.delete(artifact)

    
    def clear_protocol_shot_list_columns(self):
        self._EDFTS.revert_shot_list_columns()

    
    def play_sound(self, sound_file):
  
        self._play_sound_thread = Thread(target=self._play_sound, 
            args=(sound_file,), name="play_sound_thread")
        self._play_sound_thread.start()  

    def _play_sound(self, *args):
        chunk = 1024  
  
       
        f = wave.open(args[0],"rb")  
        p = pyaudio.PyAudio()  
        stream = p.open(format = p.get_format_from_width(f.getsampwidth()),  
                        channels = f.getnchannels(),  
                        rate = f.getframerate(),  
                        output = True)  


        data = f.readframes(chunk)   
        while data != '':  
            stream.write(data)  
            data = f.readframes(chunk)  


        stream.stop_stream()  
        stream.close()  
        p.terminate() 
