

class ITrainingProtocol():
    def __init__(self, protocol_operations, targets):
        
        pass

    def shot_listener(self, shot, shot_list_item, is_hit):
     
        pass

    def hit_listener(self, region, tags, shot, shot_list_item):
       
	pass

    def reset(self, targets):
        
        pass

    def destroy(self):
       
        pass

def get_info():
    protocol_info = {}

    protocol_info["name"] = "ITrainingProtocol"
    protocol_info["version"] = "1.0"
    protocol_info["creator"] = "Mati Ethiopia"
    desc = "The required interface for all training protocol plugins."
    protocol_info["description"] = desc

    return protocol_info

def load(protocol_operations, targets):
    return ITrainingProtocol(protocol_operations, targets)
