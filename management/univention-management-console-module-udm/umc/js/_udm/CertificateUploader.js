/*
 * Copyright 2011 Univention GmbH
 *
 * http://www.univention.de/
 *
 * All rights reserved.
 *
 * The source code of this program is made available
 * under the terms of the GNU Affero General Public License version 3
 * (GNU AGPL V3) as published by the Free Software Foundation.
 *
 * Binary versions of this program provided by Univention to you as
 * well as other copyrighted, protected or trademarked materials like
 * Logos, graphics, fonts, specific documentations and configurations,
 * cryptographic keys etc. are subject to a license agreement between
 * you and Univention and not subject to the GNU AGPL V3.
 *
 * In the case you use this program under the terms of the GNU AGPL V3,
 * the program is provided in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License with the Debian GNU/Linux or Univention distribution in file
 * /usr/share/common-licenses/AGPL-3; if not, see
 * <http://www.gnu.org/licenses/>.
 */
/*global dojo dijit dojox umc console */

dojo.provide("umc.modules._udm.CertificateUploader");

dojo.require("umc.widgets.Uploader");
dojo.require("umc.widgets.Text");

dojo.declare("umc.modules._udm.CertificateUploader", [ umc.widgets.Uploader ], {
	'class': 'umcInfoUploader',

	i18nClass: 'umc.app',

	maxSize: 512000,

	_text: null,

	constructor: function() {
		this.buttonLabel = this._( 'Upload certificate' );
		this.clearButtonLabel = this._( 'Remove certificate' );
	},

	postMixInProperties: function() {
		this.inherited(arguments);

		this.sizeClass = null;
	},

	buildRendering: function() {
		this.inherited(arguments);

		// create an text widget
		this._text = new umc.widgets.Text({
			label: '',
			content: ''
		});
		this.addChild(this._text, 0);
	},

	updateView: function(value, data) {
		if ( null === data ) {
			this._text.set( 'content', '' );
		} else if ( data.content && data.filename ) {
			this._text.set( 'content', data.filename );
		} else {
			this._text.set( 'content', this._( 'Failed to upload certificate' ) );
		}
	}
});



