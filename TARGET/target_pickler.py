import pickle
from tag_parser import TagParser

class TargetPickler():
    def save(self, target_file, region_list, canvas):
        region_object = []

        for region in region_list:
            region_coords = canvas.coords(region)
            region_fill = canvas.itemcget(region, "fill")
            region_tags = canvas.gettags(region)
	
            region_object.append({"tags":region_tags,
                "coords":region_coords,
                "fill":region_fill})

        target = open(target_file, 'wb')
        pickle.dump(region_object, target, pickle.HIGHEST_PROTOCOL)
        target.close()

    def load(self, target_file, canvas,
		internal_target_name="_internal_name:target"):

        target = open(target_file, 'rb')
        region_object = pickle.load(target)
        target.close()

        regions = self._draw_target(region_object, canvas,
			internal_target_name)
                
        return (region_object, regions)

    def _draw_target(self, region_object, canvas, internal_target_name):
        regions = []

        for region in region_object:
            shape = 0
            raw_tags = region["tags"]
    
           
            raw_tags = tuple([value for value in raw_tags if value != "_internal_name:target"])

            raw_tags += (internal_target_name,)
            parsed_tags = TagParser.parse_tags(raw_tags)	

            if parsed_tags["_shape"] == "rectangle":
                shape = canvas.create_rectangle(region["coords"],
                    fill=region["fill"], stipple="gray25",
                    tags=raw_tags)

            if parsed_tags["_shape"] == "oval":
                shape = canvas.create_oval(region["coords"],
                    fill=region["fill"], stipple="gray25",
                    tags=raw_tags)

            if parsed_tags["_shape"] == "triangle":
                shape = canvas.create_polygon(region["coords"],
                    fill=region["fill"], outline="black",
                    stipple="gray25", tags=raw_tags)

            if parsed_tags["_shape"] == "freeform_polygon":
                shape = canvas.create_polygon(region["coords"],
                    fill=region["fill"], outline="black",
                    stipple="gray25", tags=raw_tags)

            if shape != 0:
                regions.append(shape)

        return regions
