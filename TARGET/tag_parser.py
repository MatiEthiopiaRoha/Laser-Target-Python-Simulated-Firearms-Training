
class TagParser():
    @staticmethod
    def parse_tags(tag_list):
        tags = {}

        for tag in tag_list:
            if ":" not in tag: continue
            (prop, value) = tag.split(":", 1)

                        
            if prop == "command":
                if "command" not in tags:
                    tags[prop] = []

                tags[prop].append(value)
            else:            
                tags[prop] = value

        return tags
