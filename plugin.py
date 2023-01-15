#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    plugins.__init__.py

    Written by:               SenorSmartyPants@gmail.com and Josh.5 <jsunnex@gmail.com>
    Date:                     12 Jan 2023, (10:45 PM)

    Copyright:
        Copyright (C) 2023 SenorSmartyPants@gmail.com
        Copyright (C) 2021 Josh Sunnex

        This program is free software: you can redistribute it and/or modify it under the terms of the GNU General
        Public License as published by the Free Software Foundation, version 3.

        This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the
        implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
        for more details.

        You should have received a copy of the GNU General Public License along with this program.
        If not, see <https://www.gnu.org/licenses/>.

"""
import logging
import re
import json

from unmanic.libs.unplugins.settings import PluginSettings

from cleanup_titles.lib.ffmpeg import StreamMapper, Probe, Parser

# Configure plugin logger
logger = logging.getLogger("Unmanic.Plugin.cleanup_titles")


class Settings(PluginSettings):
    settings = {
        "languages": '',
        "advanced":              False,
        "main_options":          '',
        "advanced_options":      ''
    }


    def __init__(self, *args, **kwargs):
        super(Settings, self).__init__(*args, **kwargs)
        self.form_settings = {
            "languages": {
                "label": "Languages to remove",
            },
            "advanced": {
                "label": "Write your own FFmpeg params",
            },
            "main_options":          self.__set_main_options_form_settings(),
            "advanced_options":      self.__set_advanced_options_form_settings()
        }

    def __set_main_options_form_settings(self):
        values = {
            "label":      "Write your own main options",
            "input_type": "textarea",
        }
        if not self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values

    def __set_advanced_options_form_settings(self):
        values = {
            "label":      "Write your own advanced options",
            "input_type": "textarea",
        }
        if not self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values

class PluginStreamMapper(StreamMapper):
    def __init__(self):
        super(PluginStreamMapper, self).__init__(logger, ['video','audio','subtitle'])

        self.extraoptions = []

        self.settings = None

    def set_settings(self, settings):
        self.settings = settings

    def test_stream_needs_processing(self, stream_info: dict):
        """Only add streams that have title """
        if stream_info.get('tags', {}).get('title'):
            # stream has a title
            return True
        else:
            logger.warning(
                "Stream #{} in file '{}' has no 'title' tag. Ignoring".format(stream_info.get('index'), self.input_file))

        return False

    def custom_stream_mapping(self, stream_info: dict, stream_id: int):
        """Remove title"""
        codec_type = stream_info.get('codec_type', '').lower()

        match = False
        globaltitle = []
        stream_encoding = []

        # TODO check for empty global title
        if codec_type == 'video':
            #copy video stream title to global
            stitle = stream_info.get('tags', {}).get('title')
            globaltitle = ['-metadata', 'title={}'.format(stitle)]


        # TODO move this outside of stream loop
        config_json = '[{"pattern":"(?i)Original.*Dolby","replace":"Big mode"},{"pattern":"(?i)Commentary.*Dolby","replace":"Farts","disposition":"+comment"}]'
        title_options = json.loads(config_json)


        final_disposition = ''
        title = stream_info.get('tags', {}).get('title')

        # loop over all regex provided in config for matches
        for title_option in title_options:
            (title, match_count) = re.subn(title_option.get('pattern'), title_option.get('replace'), title)

            if match_count:
                match = True
                if title_option.get('disposition'):
                    final_disposition += title_option.get('disposition') + ' '

        if match:
            stream_encoding = (['-metadata:s:{}:{}'.format(codec_type[0], stream_id), 'title={}'.format(title)])
            if final_disposition:
                self.extraoptions += ['-disposition:{}:{}'.format(codec_type[0], stream_id), final_disposition.strip()]

        return {
            'stream_mapping':  globaltitle,
            'stream_encoding': stream_encoding
        }

    def append_extraoptions(self):
        self.stream_encoding += self.extraoptions

def on_library_management_file_test(data):
    """
    Runner function - enables additional actions during the library management file tests.

    The 'data' object argument includes:
        path                            - String containing the full path to the file being tested.
        issues                          - List of currently found issues for not processing the file.
        add_file_to_pending_tasks       - Boolean, is the file currently marked to be added to the queue for processing.

    :param data:
    :return:

    """
    # Configure settings object (maintain compatibility with v1 plugins)
    if data.get('library_id'):
        settings = Settings(library_id=data.get('library_id'))
    else:
        settings = Settings()

    # If the config is empty (not yet configured) ignore everything
    if not settings.get_setting('languages'):
        logger.debug("Plugin has not yet been configured with a list of file extensions to allow. Blocking everything.")
        return False

    # Get the path to the file
    abspath = data.get('path')

    # Get file probe
    probe = Probe(logger, allowed_mimetypes=['video'])
    if not probe.file(abspath):
        # File probe failed, skip the rest of this test
        return data

    # Get stream mapper
    mapper = PluginStreamMapper()
    mapper.set_settings(settings)
    mapper.set_probe(probe)

    # Set the input file
    mapper.set_input_file(abspath)

    # TODO: check global tags

    if mapper.streams_need_processing():
        # Mark this file to be added to the pending tasks
        data['add_file_to_pending_tasks'] = True
        logger.debug("File '{}' should be added to task list. Probe found streams require processing.".format(abspath))
    else:
        logger.debug("File '{}' does not contain streams that require processing.".format(abspath))

    del mapper

    return data


def on_worker_process(data):
    """
    Runner function - enables additional configured processing jobs during the worker stages of a task.

    The 'data' object argument includes:
        exec_command            - A command that Unmanic should execute. Can be empty.
        command_progress_parser - A function that Unmanic can use to parse the STDOUT of the command to collect progress stats. Can be empty.
        file_in                 - The source file to be processed by the command.
        file_out                - The destination that the command should output (may be the same as the file_in if necessary).
        original_file_path      - The absolute path to the original file.
        repeat                  - Boolean, should this runner be executed again once completed with the same variables.

    :param data:
    :return:

    """
    # Default to no FFMPEG command required. This prevents the FFMPEG command from running if it is not required
    data['exec_command'] = []
    data['repeat'] = False

    # Get the path to the file
    abspath = data.get('file_in')

    # Get file probe
    probe = Probe(logger, allowed_mimetypes=['video'])
    if not probe.file(abspath):
        # File probe failed, skip the rest of this test
        return data

    # Configure settings object (maintain compatibility with v1 plugins)
    if data.get('library_id'):
        settings = Settings(library_id=data.get('library_id'))
    else:
        settings = Settings()

    # Get stream mapper
    mapper = PluginStreamMapper()
    mapper.set_settings(settings)
    mapper.set_probe(probe)

    # Set the input file
    mapper.set_input_file(abspath)

    if mapper.streams_need_processing():
        # Set the output file
        mapper.set_output_file(data.get('file_out'))

        # copy everything
        mapper.main_options += ['-map', '0', '-c', 'copy']

        if settings.get_setting('advanced'):
            mapper.main_options += settings.get_setting('main_options').split()
            mapper.advanced_options += settings.get_setting('advanced_options').split()

        # check global title

        # check for single streams
        if mapper.video_stream_count == 1:
            mapper.extraoptions += ['-metadata:s:v:0', 'title=']

        if mapper.audio_stream_count == 1:
            mapper.extraoptions += ['-metadata:s:a:0', 'title=']

        if mapper.subtitle_stream_count == 1:
            mapper.extraoptions += ['-metadata:s:s:0', 'title=']

        # Append extraoptions
        mapper.append_extraoptions()

        # Get generated ffmpeg args
        ffmpeg_args = mapper.get_ffmpeg_args()

        # Apply ffmpeg args to command
        data['exec_command'] = ['ffmpeg']
        data['exec_command'] += ffmpeg_args

        # Set the parser
        parser = Parser(logger)
        parser.set_probe(probe)
        data['command_progress_parser'] = parser.parse_progress

    return data
