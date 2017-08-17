#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# UCS Installer Tests
#
# Copyright 2017 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

import pytest
import ConfigParser

config = ConfigParser.SafeConfigParser()
config.read('tests.cfg')

i = 1


@pytest.fixture
def language():
	return config.get('General', 'language').split('-', 1)[0]


@pytest.fixture
def server():
	return config.get('General', 'server')


@pytest.fixture
def iso_image():
	return config.get('General', 'isoimage')


@pytest.fixture(scope='function')
def ip_address():
	global i
	i += 1
	return '%s.%s' % (config.get('General', 'iprange'), i)