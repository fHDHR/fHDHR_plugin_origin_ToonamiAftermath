import datetime
import pytz
import urllib.parse


class Plugin_OBJ():

    def __init__(self, channels, plugin_utils):
        self.plugin_utils = plugin_utils

        self.channels = channels

        self.origin = plugin_utils.origin

        self.base_api = 'http://api.toonamiaftermath.com:3000'
        self.media_url = "%s/media" % self.base_api

    def update_epg(self):
        programguide = {}

        datestrings = []
        todaydate = datetime.date.today()
        for x in range(0, 6):
            xdate = todaydate + datetime.timedelta(days=x)
            datestrings.append(str(xdate))

        self.remove_stale_cache(todaydate)

        for fhdhr_id in list(self.channels.list[self.plugin_utils.namespace].keys()):
            chan_obj = self.channels.list[self.plugin_utils.namespace][fhdhr_id]

            if str(chan_obj.number) not in list(programguide.keys()):
                programguide[chan_obj.number] = chan_obj.epgdict

            if chan_obj.dict["origin_id"] in ["est", "pst", "snick-est", "snick-pst"]:

                epgname = chan_obj.dict["origin_id"]
                if "pst" in chan_obj.dict["origin_id"]:
                    epgname = chan_obj.dict["origin_id"].replace("pst", "est")

                datestring = str(datetime.date.today())

                if chan_obj.dict["origin_id"] in ["est", "pst"]:
                    schedule_name = "Toonami Aftermath"
                elif chan_obj.dict["origin_id"] in ["snick-est", "snick-pst"]:
                    schedule_name = "Snickelodeon"

                schedulename_quote = urllib.parse.quote("%s EST" % schedule_name)

                epgguide = []
                for datestring in datestrings:
                    schedule_url = ("%s?scheduleName=%s"
                                    "&dateString=%s"
                                    "&count=150" %
                                    (self.media_url, schedulename_quote, datestring))
                    curr_epg = self.get_cached(epgname, datestring, schedule_url)
                    if curr_epg:
                        epgguide.extend(curr_epg)

                offset = '+00:00'
                if "pst" in chan_obj.dict["origin_id"]:
                    offset = '-03:00'

                progindex = 0
                for program_dict in epgguide:

                    try:
                        nextprog_dict = epgguide[progindex + 1]
                    except IndexError:
                        nextprog_dict = None
                    if nextprog_dict:

                        timedict = self.get_prog_timedict(program_dict["startDate"], nextprog_dict["startDate"], offset)

                        try:
                            subtitle = program_dict["name"]
                        except KeyError:
                            subtitle = "Unavailable"

                        try:
                            title = program_dict["info"]["fullname"]
                        except KeyError:
                            title = subtitle

                        try:
                            thumbnail = program_dict["info"]["image"]
                        except KeyError:
                            thumbnail = ("/api/images?method=generate&type=content&message=%s_%s" % (chan_obj.dict["origin_id"], str(timedict['time_start']).split(" ")[0]))

                        clean_prog_dict = {
                                            "time_start": timedict['time_start'],
                                            "time_end": timedict['time_end'],
                                            "duration_minutes": timedict["duration"],
                                            "thumbnail": thumbnail,
                                            "title": title,
                                            "sub-title": subtitle,
                                            "description": "Unavailable",
                                            "rating": "N/A",
                                            "episodetitle": None,
                                            "releaseyear": None,
                                            "genres": [],
                                            "seasonnumber": None,
                                            "episodenumber": None,
                                            "isnew": False,
                                            "id": "%s_%s" % (chan_obj.dict["origin_id"], str(timedict['time_start']).split(" ")[0]),
                                            }

                        if not any((d['time_start'] == clean_prog_dict['time_start'] and d['id'] == clean_prog_dict['id']) for d in programguide[chan_obj.number]["listing"]):
                            programguide[chan_obj.number]["listing"].append(clean_prog_dict)

                    progindex += 1

        return programguide

    def toonami_calculate_duration(self, start_time, end_time):
        start_time = start_time.replace('Z', '+00:00')
        start_time = datetime.datetime.fromisoformat(start_time)

        end_time = end_time.replace('Z', '+00:00')
        end_time = datetime.datetime.fromisoformat(end_time)

        duration = (end_time - start_time).total_seconds() / 60
        return duration

    def xmltimestamp_toonami(self, inputtime, offset):
        xmltime = inputtime.replace('Z', offset)
        xmltime = datetime.datetime.fromisoformat(xmltime)
        xmltime = xmltime.strftime('%Y%m%d%H%M%S %z')
        if offset != '+00:00':
            xmltime = datetime.datetime.strptime(xmltime, "%Y%m%d%H%M%S %z")
            xmltime = xmltime.astimezone(pytz.utc)
            xmltime = xmltime.strftime('%Y%m%d%H%M%S %z')
        xmltime = datetime.datetime.strptime(xmltime, "%Y%m%d%H%M%S %z")
        xmltime = xmltime.timestamp()
        return xmltime

    def get_prog_timedict(self, starttime, endtime, offset):
        timedict = {
                    "time_start": self.xmltimestamp_toonami(starttime, offset),
                    "time_end": self.xmltimestamp_toonami(endtime, offset),
                    "duration": str(int(self.toonami_calculate_duration(starttime, endtime)))
                    }
        return timedict

    def get_cached(self, jsonid, cache_key, url):
        cacheitem = self.plugin_utils.db.get_plugin_value("%s_%s" % (jsonid, cache_key), "offline_cache", "toonamiaftermath")
        if cacheitem:
            self.plugin_utils.logger.info("FROM CACHE:  %s" % cache_key)
            return cacheitem
        else:
            self.plugin_utils.logger.info("Fetching:  %s" % url)
            try:
                resp = self.plugin_utils.web.session.get(url)
            except self.plugin_utils.web.exceptions.HTTPError:
                self.plugin_utils.logger.info('Got an error!  Ignoring it.')
                return
            result = resp.json()

            self.plugin_utils.db.set_plugin_value("%s_%s" % (jsonid, cache_key), "offline_cache", result, "toonamiaftermath")
            cache_list = self.plugin_utils.db.get_plugin_value("cache_list", "offline_cache", "toonamiaftermath") or []
            cache_list.append("%s_%s" % (jsonid, cache_key))
            self.plugin_utils.db.set_plugin_value("cache_list", "offline_cache", cache_list, "toonamiaftermath")

    def remove_stale_cache(self, todaydate):
        cache_list = self.plugin_utils.db.get_plugin_value("cache_list", "offline_cache", "toonamiaftermath") or []
        cache_to_kill = []
        for cacheitem in cache_list:
            cachedate = datetime.datetime.strptime(str(cacheitem).split("_")[-1], "%Y-%m-%d")
            todaysdate = datetime.datetime.strptime(str(todaydate), "%Y-%m-%d")
            if cachedate < todaysdate:
                cache_to_kill.append(cacheitem)
                self.plugin_utils.db.delete_plugin_value(cacheitem, "offline_cache", "toonamiaftermath")
                self.plugin_utils.logger.info("Removing stale cache:  %s" % cacheitem)
        self.plugin_utils.db.set_plugin_value("cache_list", "offline_cache", [x for x in cache_list if x not in cache_to_kill], "toonamiaftermath")

    def clear_cache(self):
        cache_list = self.plugin_utils.db.get_plugin_value("cache_list", "offline_cache", "toonamiaftermath") or []
        for cacheitem in cache_list:
            self.plugin_utils.db.delete_plugin_value(cacheitem, "offline_cache", "toonamiaftermath")
            self.plugin_utils.logger.info("Removing cache:  %s" % cacheitem)
        self.plugin_utils.db.delete_plugin_value("cache_list", "offline_cache", "toonamiaftermath")
