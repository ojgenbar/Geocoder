#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cPickle as pickle
import json
import os.path
import time
import urllib


class GeocoderResult:
    def __init__(self):
        self.lat = None
        self.long = None
        self.address = None
        self.kind = None
        self.success = None
        self.message = None

    def __repr__(self):
        addr = self.address or u'None'
        addr = addr.encode('UTF-8')
        kind = self.kind.encode('UTF-8')
        return '<Class GeocoderResult(success=%s, lat=%s, long=%s, address="%s", kind="%s")>'% \
               (self.success, self.lat, self.long, addr, kind)

class Geocoder:
    def __init__(self):

        self.machine = 0

        self.lang = 4  # language: 'ru_RU', 'uk_UA', 'be_BY', 'en_RU', 'en_US', 'tr_TR'
        self.ll = ()
        self.spn = ()
        self.rspn = None
        self.results = None
        self.kind = None

        # Жесткое соответствие типа "kind" и ответа сервера
        self.strictMatch = False

        self.offlineMod = False

        self.YAcache = {}
        self.YAcacheNew = {}
        self.YAcacheUsed = False
        self.path = os.path.dirname(__file__)

        self.responses = {}

    def geocodeYA(self, address):

        if not self.YAcacheUsed:
            self.loadCache()
            self.YAcacheUsed = True

        serviceurl = "https://geocode-maps.yandex.ru/1.x/?"
        langlst = ['ru_RU', 'uk_UA', 'be_BY', 'en_RU', 'en_US', 'tr_TR']

        try:
            lang = langlst[self.lang]
        except IndexError:
            lang = 'en_US'

        qres = str(self.results)
        ll = ','.join([str(i) for i in self.ll])
        spn = ','.join([str(i) for i in self.spn])
        rspn = str(self.rspn)

        paramKey = (address, lang, qres, ll, spn, rspn)
        if paramKey in self.YAcache:
            geocoded = self.YAcache[paramKey]
            return geocoded
        else:
            geocoded = GeocoderResult()
            print 'Making request...'

            ##################
            # OFFLINE VERSION
            if self.offlineMod:
                print 'IT IS OFFLINE VERSION!!!'
                geocoded.success = False
                geocoded.message = 'IT IS OFFLINE VERSION!!!'
                return geocoded
            #################

            params = {
                'format': 'json',
                'geocode': address,
                'lang': lang,
            }
            if self.results: params['results'] = qres
            if self.ll: params['ll'] = ll
            if self.spn: params['spn'] = spn
            if self.kind: params['kind'] = self.kind
            if self.rspn: params['rspn'] = rspn

            try:
                url = serviceurl + urllib.urlencode(params)
            except UnicodeEncodeError:
                params['geocode'] = address.encode('utf-8')
                url = serviceurl + urllib.urlencode(params)

            # Retrieving url
            uh = None
            for attempt in range(10):
                try:
                    uh = urllib.urlopen(url)
                    break
                except IOError:
                    print 'Repeating request.Wait 5 seconds...'
                    time.sleep(5)

            if not uh:
                geocoded.success = False
                geocoded.message = '\n'.join(['Unknown failure with response.', url])
                return geocoded

            data = uh.read()

            try:
                js = json.loads(str(data))
            except Exception:
                js = None

            try:
                js2 = js["response"]["GeoObjectCollection"]["metaDataProperty"]["GeocoderResponseMetaData"]
            except Exception:
                geocoded.success = False
                geocoded.message = '\n'.join(['Unknown failure with response.', data, url])
                return geocoded


            if 'found' not in js2 or js2['found'] == '0':
                message = '\n'.join(['==== Failure To Geocode ====', data, url])
                geocoded.success = False
                geocoded.message = message
                return geocoded
            else:
                location = js["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]["metaDataProperty"][
                    "GeocoderMetaData"]["text"]
                longlat = js["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]["Point"][
                    "pos"].strip().split(' ')
                geocoded.lat = float(longlat[1])
                geocoded.long = float(longlat[0])
                geocoded.address = location
                retrievedKind = \
                    js["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]["metaDataProperty"][
                        "GeocoderMetaData"]["kind"]
                geocoded.kind = retrievedKind
                geocoded.success = True

                if self.strictMatch:
                    if not (self.kind == retrievedKind):
                        message = 'Retrieved kind "%s" is not "%s"' % (retrievedKind, self.kind)
                        print message
                        geocoded.success = False
                        geocoded.message = message
                        return geocoded

                self.YAcacheNew[paramKey] = geocoded
                if geocoded.success:
                    self.responses[paramKey] = data
                time.sleep(0.1)
                return geocoded

    def geocode(self, address):

        return self.geocodeYA(address)

    def loadCache(self):
        try:
            self.path = os.path.dirname(__file__)
            with open(os.path.join(self.path, 'YAcache'), 'rb') as f:
                self.YAcache = pickle.load(f)
        except IOError:
            self.YAcache = {}

    def loadResponses(self):
        try:
            self.path = os.path.dirname(__file__)
            with open(os.path.join(self.path, 'YAresponses'), 'rb') as f:
                old_responses = pickle.load(f)
            return old_responses
        except IOError:
            return {}

    def saveCache(self):

        if self.YAcacheNew:
            self.loadCache()
            try:
                f = open(os.path.join(self.path, 'YAcache'), 'wb')
                self.YAcache.update(self.YAcacheNew)
                pickle.dump(self.YAcache, f)
            except IOError or ValueError:
                time.sleep(2)
                f = open(os.path.join(self.path, 'YAcache'), 'wb')
                pickle.dump(self.YAcache, f)
            f.close()
            self.YAcacheNew = {}

        if self.responses:
            old = self.loadResponses()
            try:
                f = open(os.path.join(self.path, 'YAresponses'), 'wb')
                old.update(self.responses)
                pickle.dump(old, f)
            except IOError or ValueError:
                time.sleep(2)
                f = open(os.path.join(self.path, 'YAresponses'), 'wb')
                pickle.dump(old, f)
            f.close()
            self.responses = {}


if __name__ == '__main__':

    en_geo = Geocoder()
    en_geo.lang = 4
    en_geo.results = 1
    en_geo.ll = (31.293352, 60.018353)
    en_geo.spn = (10, 4)
    en_geo.rspn = '1'
    res = en_geo.geocode(u"Жуковского ул. 7")
    try:
        if res.success:
            print res.lat, res.long
            print res.address.encode('utf-8')
            print res.kind.encode('utf-8')
            print res

        else:
            print res.message
    except ZeroDivisionError:
        for i in res:
            print i.encode('utf-8')
    en_geo.saveCache()

    # path = os.path.dirname(__file__)
    # f = open(os.path.join(path, 'YAresponses'), 'rb')
    # old_responses = pickle.load(f)
    # f.close()
    # print old_responses[old_responses.keys()[0]]
    # en = Geocoder()
    # en.saveCache()

