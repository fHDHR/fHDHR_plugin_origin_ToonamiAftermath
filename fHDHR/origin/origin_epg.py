import datetime
import pytz
import urllib.parse


class OriginEPG():

    def __init__(self, fhdhr):
        self.fhdhr = fhdhr

        self.base_api = 'http://api.toonamiaftermath.com:3000'
        self.media_url = "%s/media" % self.base_api

    def update_epg(self, fhdhr_channels):
        programguide = {}

        datestrings = []
        timestamps = []
        todaydate = datetime.date.today()
        for x in range(0, 6):
            xdate = todaydate + datetime.timedelta(days=x)
            xtdate = xdate + datetime.timedelta(days=1)

            datestrings.append(str(xdate))

            for hour in range(0, 24):
                time_start = datetime.datetime.combine(xdate, datetime.time(hour, 0))
                if hour + 1 < 24:
                    time_end = datetime.datetime.combine(xdate, datetime.time(hour + 1, 0))
                else:
                    time_end = datetime.datetime.combine(xtdate, datetime.time(0, 0))
                timestampdict = {
                                "time_start": str(time_start.strftime('%Y%m%d%H%M%S')) + " +0000",
                                "time_end": str(time_end.strftime('%Y%m%d%H%M%S')) + " +0000",
                                }
                timestamps.append(timestampdict)

        self.remove_stale_cache(todaydate)

        for fhdhr_id in list(fhdhr_channels.list.keys()):
            c = fhdhr_channels.list[fhdhr_id].dict

            if str(c["number"]) not in list(programguide.keys()):
                programguide[str(c["number"])] = {
                                                    "callsign": c["callsign"],
                                                    "name": c["name"],
                                                    "number": c["number"],
                                                    "id": c["origin_id"],
                                                    "thumbnail": c["thumbnail"] or ("/api/images?method=generate&type=channel&message=%s" % (str(c['number']))),
                                                    "listing": [],
                                                    }
            if c["origin_id"] in ["est", "pst", "snick-est", "snick-pst"]:
                epgname = c["origin_id"]
                if "pst" in c["origin_id"]:
                    epgname = c["origin_id"].replace("pst", "est")
                datestring = str(datetime.date.today())
                if c["origin_id"] in ["est", "pst"]:
                    schedule_name = "Toonami Aftermath"
                elif c["origin_id"] in ["snick-est", "snick-pst"]:
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
                if "pst" in c["origin_id"]:
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
                            thumbnail = ("/api/images?method=generate&type=content&message=%s" % (str(c["origin_id"]) + "_" + str(timedict['time_start']).split(" ")[0]))

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
                                            "id": str(c["origin_id"]) + "_" + str(timedict['time_start']).split(" ")[0],
                                            }
                        programguide[str(c["number"])]["listing"].append(clean_prog_dict)

                    progindex += 1

            else:

                for timestamp in timestamps:
                    clean_prog_dict = {
                                        "time_start": timestamp['time_start'],
                                        "time_end": timestamp['time_end'],
                                        "duration_minutes": 60,
                                        "thumbnail": ("/api/images?method=generate&type=content&message=%s" % (str(c["origin_id"]) + "_" + str(timestamp['time_start']).split(" ")[0])),
                                        "title": "Unavailable",
                                        "sub-title": "Unavailable",
                                        "description": "Unavailable",
                                        "rating": "N/A",
                                        "episodetitle": None,
                                        "releaseyear": None,
                                        "genres": [],
                                        "seasonnumber": None,
                                        "episodenumber": None,
                                        "isnew": False,
                                        "id": str(c["origin_id"]) + "_" + str(timestamp['time_start']).split(" ")[0],
                                        }

                    programguide[str(c["number"])]["listing"].append(clean_prog_dict)

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
        return xmltime

    def get_prog_timedict(self, starttime, endtime, offset):
        timedict = {
                    "time_start": self.xmltimestamp_toonami(starttime, offset),
                    "time_end": self.xmltimestamp_toonami(endtime, offset),
                    "duration": str(int(self.toonami_calculate_duration(starttime, endtime)))
                    }
        return timedict

    def get_cached(self, jsonid, cache_key, url):
        cacheitem = self.fhdhr.db.get_cacheitem_value(jsonid + "_" + str(cache_key), "offline_cache", "origin")
        if cacheitem:
            self.fhdhr.logger.info('FROM CACHE:  ' + jsonid + "_" + str(cache_key))
            return cacheitem
        else:
            self.fhdhr.logger.info('Fetching:  ' + url)
            try:
                resp = self.fhdhr.web.session.get(url)
            except self.fhdhr.web.exceptions.HTTPError:
                self.fhdhr.logger.info('Got an error!  Ignoring it.')
                return
            result = resp.json()

            self.fhdhr.db.set_cacheitem_value(jsonid + "_" + str(cache_key), "offline_cache", result, "origin")
            cache_list = self.fhdhr.db.get_cacheitem_value("cache_list", "offline_cache", "origin") or []
            cache_list.append(jsonid + "_" + str(cache_key))
            self.fhdhr.db.set_cacheitem_value("cache_list", "offline_cache", cache_list, "origin")

    def remove_stale_cache(self, todaydate):
        cache_list = self.fhdhr.db.get_cacheitem_value("cache_list", "offline_cache", "origin") or []
        cache_to_kill = []
        for cacheitem in cache_list:
            cachedate = datetime.datetime.strptime(str(cacheitem).split("_")[-1], "%Y-%m-%d")
            todaysdate = datetime.datetime.strptime(str(todaydate), "%Y-%m-%d")
            if cachedate < todaysdate:
                cache_to_kill.append(cacheitem)
                self.fhdhr.db.delete_cacheitem_value(cacheitem, "offline_cache", "origin")
                self.fhdhr.logger.info('Removing stale cache:  ' + str(cacheitem))
        self.fhdhr.db.set_cacheitem_value("cache_list", "offline_cache", [x for x in cache_list if x not in cache_to_kill], "origin")

    def clear_cache(self):
        cache_list = self.fhdhr.db.get_cacheitem_value("cache_list", "offline_cache", "origin") or []
        for cacheitem in cache_list:
            self.fhdhr.db.delete_cacheitem_value(cacheitem, "offline_cache", "origin")
            self.fhdhr.logger.info('Removing cache:  ' + str(cacheitem))
        self.fhdhr.db.delete_cacheitem_value("cache_list", "offline_cache", "origin")
