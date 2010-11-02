# -*- coding: utf8 -*-
# Share online provider settings

service_id = 'com.example.shareonline' # Mandatory and unique for your app
post_url = '/service' # Returns list of feeds (or channels), mandatory

# Provider
provider = {}
provider['configure_file_URL'] = '/config' # Returns configuration file (the URL of this file), mandatory
provider['signup_URL'] = None
provider['easy_registration_URL'] = None

laf = {}
laf['title'] = 'Shareonline demo' # Title to show in Online Share's provider list
laf['icon_svg_path'] = 'defaulticon.svg' # Full path to the icon file

media_options = {}
media_options['format_list'] = [ # Supported mimetypes or file formats
    'image/jpeg', 'image/png',
    'video/mp4', 'video/3gpp',
    'audio/amr', 'audio/wav', 'audio/mp3',
]
# File size options, set all to '0' if you don't want to have limits
media_options['maximum_pixels'] = {'horizontal': '0', 'vertical': '0'}
media_options['maximum_bytes'] = {'bytes': '0'}

# Visible and required fields in Share online application
entry_options = {}
entry_options['title_text'] = {'present': '0', 'required': '0'}
entry_options['caption_text'] = {'present': '1', 'required': '0'}
entry_options['body_text'] = {'present': '0', 'required': '0'}
entry_options['min_items'] = {'items': '1'}
entry_options['max_items'] = {'items': '1'}
entry_options['max_size'] = {'size': '0'}
entry_options['tags'] = {'present': '1', 'required': '0'}
entry_options['privacy_levels'] = {'present': '1', 'required': '0'}

# Whether or not to include location information (if abailable) in the post
location_options = {}
location_options['gps_info'] = {'present': '1'}
location_options['network_info'] = {'present': '1'}
##############################################################################
