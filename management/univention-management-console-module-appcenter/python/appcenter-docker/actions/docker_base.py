#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention App Center
#  univention-app mixin for dockerized actions
#
# Copyright 2015 Univention GmbH
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
#

import shutil
import os.path
import re
import requests
import hashlib

from ldap.dn import explode_dn

from univention.config_registry import ConfigRegistry

from univention.appcenter.docker import Docker
from univention.appcenter.actions import Abort, get_action
from univention.appcenter.actions.service import Start
from univention.appcenter.utils import mkdir


class DockerActionMixin(object):
	@classmethod
	def _get_docker(cls, app):
		if not app.docker:
			return
		return Docker(app, cls.logger)

	def _execute_container_script(self, _app, _interface, _args=None, _credentials=True, _output=False, **kwargs):
		self.log('Executing interface %s for %s' % (_interface, _app.id))
		docker = self._get_docker(_app)
		interface = getattr(_app, 'docker_script_%s' % _interface)
		if not interface:
			self.log('No interface defined')
			return None
		remote_interface_script = _app.get_cache_file(_interface)
		container_interface_script = docker.path(interface)
		if os.path.exists(remote_interface_script):
			self.log('Copying App Center\'s %s to container\'s %s' % (_interface, interface))
			mkdir(os.path.dirname(container_interface_script))
			shutil.copy2(remote_interface_script, container_interface_script)
			os.chmod(container_interface_script, 0755)  # -rwxr-xr-x
		if not os.path.exists(container_interface_script):
			self.warn('Interface script %s not found!' % interface)
			return None
		error_file = docker.execute_with_output('mktemp').strip()
		if _credentials:
			password_file = docker.execute_with_output('mktemp').strip()
			self._get_ldap_connection(_args)  # to get a working username/password
			username = self._get_username(_args)
			password = self._get_password(_args)
			with open(docker.path(password_file), 'w') as f:
				f.write(password)
			kwargs['username'] = username
			kwargs['password_file'] = password_file
		kwargs['error_file'] = error_file
		kwargs['app'] = _app.id
		kwargs['app_version'] = _app.version
		try:
			if _output:
				return docker.execute_with_output(interface, **kwargs)
			else:
				process = docker.execute(interface, **kwargs)
				if process.returncode != 0:
					with open(docker.path(error_file), 'r+b') as error_handle:
						for line in error_handle:
							self.warn(line)
				return process
		finally:
			if _credentials:
				docker.execute('rm', password_file)
			docker.execute('rm', error_file)

	def _start_docker_image(self, app, hostdn, password, args):
		docker = self._get_docker(app)
		if not docker:
			return

		self.log('Downloading app image %s. This may take several minutes' % docker.image)
		docker.pull()

		self.log('Verifying app image %s' % docker.image)
		try:
			hub, image_name = docker.image.split('/', 1)
		except ValueError:
			image_name = docker.image

		docker_image_name_parts = image_name.split(':', 1)
		docker_image_repo = docker_image_name_parts[0]
		if len(docker_image_name_parts) > 1:
			docker_image_tag = docker_image_name_parts[1]
		else:
			docker_image_tag = 'latest'

		docker_image_manifest = requests.get('https://ucs:readonly@docker.software-univention.de/v2/%s/manifests/%s' % (docker_image_repo, docker_image_tag), auth=requests.auth.HTTPBasicAuth('ucs', 'readonly')).content
		docker_image_manifest_hash = hashlib.sha256(docker_image_manifest).hexdigest()
		## TODO: verify
		
		self.log('Initializing app image')
		ucr = ConfigRegistry()
		ucr.load()
		hostname = explode_dn(hostdn, 1)[0]
		set_vars = (args.set_vars or {}).copy()
		configure = get_action('configure')
		for variable in configure.list_config(app):
			if variable['value'] is not None and variable['id'] not in set_vars:
				set_vars[variable['id']] = variable['value']  # default
		set_vars['ldap/hostdn'] = hostdn
		set_vars['server/role'] = app.docker_server_role
		set_vars['update/warning/releasenotes'] = 'no'
		for var in ['nameserver.*', 'repository/online/server', 'repository/app_center/server', 'update/secure_apt', 'ldap/master.*', 'locale.*', 'domainname']:
			for key in ucr.iterkeys():
				if re.match(var, key):
					set_vars[key] = ucr.get(key)
		set_vars['updater/identify'] = 'Docker App'
		container = docker.create(hostname, set_vars)
		self.log('Preconfiguring container %s' % container)
		autostart = 'yes'
		if not Start.call(app=app):
			self.fatal('Unable to start the container!')
			raise Abort()
		if password:
			with open(docker.path('/etc/machine.secret'), 'w+b') as f:
				f.write(password)
		configure.call(app=app, autostart=autostart, set_vars=set_vars)
