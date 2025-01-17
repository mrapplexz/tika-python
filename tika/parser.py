#!/usr/bin/env python
# encoding: utf-8
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from .tika import parse1, callServer, ServerEndpoint
import logging
import os
import json

log = logging.getLogger('tika.parser')


def from_file(filename, serverEndpoint=ServerEndpoint, service='all', xmlContent=False, headers=None, config_path=None, requestOptions={}, raw_response=False):
    '''
    Parses a file for metadata and content
    :param filename: path to file which needs to be parsed or binary file using open(path,'rb')
    :param serverEndpoint: Server endpoint url
    :param service: service requested from the tika server
                    Default is 'all', which results in recursive text content+metadata.
                    'meta' returns only metadata
                    'text' returns only content
    :param xmlContent: Whether or not XML content be requested.
                    Default is 'False', which results in text content.
    :param headers: Request headers to be sent to the tika reset server, should
                    be a dictionary. This is optional
    :return: dictionary having 'metadata' and 'content' keys.
            'content' has a str value and metadata has a dict type value.
    '''
    services = {'meta': '/meta', 'text': '/tika', 'all': '/rmeta/text'}
    if xmlContent:
        services['all'] = '/rmeta/xml'

    output = parse1(service, filename, serverEndpoint, services=services,
                    headers=headers, config_path=config_path, requestOptions=requestOptions)
    if raw_response:
        return output
    return _parse(output, service)


def from_buffer(string, serverEndpoint=ServerEndpoint, xmlContent=False, headers=None, config_path=None, requestOptions={}, raw_response=False):
    '''
    Parses the content from buffer
    :param string: Buffer value
    :param serverEndpoint: Server endpoint. This is optional
    :param xmlContent: Whether or not XML content be requested.
                    Default is 'False', which results in text content.
    :param headers: Request headers to be sent to the tika reset server, should
                    be a dictionary. This is optional
    :return:
    '''
    headers = headers or {}
    headers.update({'Accept': 'application/json'})

    service = '/rmeta/text'

    if xmlContent:
        service = '/rmeta/xml'

    status, response = callServer('put', serverEndpoint, service, string,
                                  headers, False, config_path=config_path, requestOptions=requestOptions)

    if raw_response:
        return (status, response)

    return _parse((status, response))


def _parse(output, service='all'):
    '''
    Parses response from Tika REST API server
    :param output: output from Tika Server
    :param service: service requested from the tika server
                    Default is 'all', which results in recursive text content+metadata.
                    'meta' returns only metadata
                    'text' returns only content
    :return: a dictionary having 'metadata' and 'content' values
    '''
    parsed = {'metadata': None, 'content': None}
    if not output:
        return parsed

    parsed["status"] = output[0]
    if output[1] == None or output[1] == "":
        return parsed

    if service == "text":
        parsed["content"] = output[1]
        return parsed

    realJson = json.loads(output[1])

    parsed["metadata"] = {}
    if service == "meta":
        for key in realJson:
            parsed["metadata"][key] = realJson[key]
        return parsed

    content = ""
    for js in realJson:
        if "X-TIKA:content" in js:
            content += js["X-TIKA:content"]

    if content == "":
        content = None

    parsed["content"] = content

    embeddedFile = []
    for js in realJson:
        for n in js:
            if n != "X-TIKA:content":
                if n in parsed["metadata"]:
                    if not isinstance(parsed["metadata"][n], list):
                        parsed["metadata"][n] = [parsed["metadata"][n]]
                    parsed["metadata"][n].append(js[n])
                else:
                    parsed["metadata"][n] = js[n]

                if n == "embeddedRelationshipId" and js["embeddedRelationshipId"]:
                    embeddedFile.append(js["embeddedRelationshipId"])

    if embeddedFile:
        log.info("Embedded files {}", embeddedFile)

    return parsed
