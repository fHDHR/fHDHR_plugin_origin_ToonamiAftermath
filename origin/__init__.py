

class Plugin_OBJ():

    def __init__(self, plugin_utils):
        self.plugin_utils = plugin_utils

        self.channel_json_url = "https://www.toonamiaftermath.com/tatv.json"
        self.base_api = 'http://api.toonamiaftermath.com:3000'
        self.stream_url_base = "%s/streamUrl?&channelName=" % self.base_api

    @property
    def tuners(self):
        return self.plugin_utils.config.dict["toonamiaftermath"]["tuners"]

    @property
    def stream_method(self):
        return self.plugin_utils.config.dict["toonamiaftermath"]["stream_method"]

    def get_channels(self):

        channel_list = []
        channels_json = self.plugin_utils.web.session.get(self.channel_json_url).json()
        for channel_dict in channels_json["channels"]:

            clean_station_item = {
                                 "name": channel_dict["title"],
                                 "callsign": channel_dict["id"].title(),
                                 "id": channel_dict["id"],
                                 }
            channel_list.append(clean_station_item)

        movie_channel = {
                         "name": "Toonami Aftermath's Random Movies",
                         "callsign": "Movies",
                         "id": "movies",
                         }
        channel_list.append(movie_channel)

        snickelodeon_est_channel = {
                                     "name": "Snickelodeon (Eastern Time)",
                                     "callsign": "SNick-EST",
                                     "id": "snick-est",
                                     }
        channel_list.append(snickelodeon_est_channel)
        snickelodeon_pst_channel = {
                                     "name": "Snickelodeon (Pacific Time)",
                                     "callsign": "SNick-PST",
                                     "id": "snick-pst",
                                     }
        channel_list.append(snickelodeon_pst_channel)

        mtv97_est_channel = {
                             "name": "MTV97 (Eastern Time)",
                             "callsign": "MTV97-EST",
                             "id": "mtv97",
                             }
        channel_list.append(mtv97_est_channel)
        mtv97_pst_channel = {
                             "name": "MTV97 (Pacific Time)",
                             "callsign": "MTV97-PST",
                             "id": "mtv97-PSToff",
                             }
        channel_list.append(mtv97_pst_channel)

        return channel_list

    def get_channel_stream(self, chandict, stream_args):
        if "pst" in chandict["origin_id"]:
            streamurl = self.stream_url_base + chandict["origin_id"].replace("pst", "est")
            streamurl += "&streamDelay=180"
        elif "-PSToff" in chandict["origin_id"]:
            streamurl = self.stream_url_base + chandict["origin_id"].replace("-PSToff", "")
            streamurl += "&streamDelay=180"
        else:
            streamurl = self.stream_url_base + chandict["origin_id"]
        streamurl = self.plugin_utils.web.session.get(streamurl).text

        stream_info = {"url": streamurl}

        return stream_info
