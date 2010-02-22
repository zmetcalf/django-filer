/*
 * file browser for django-filer
 * http://github.com/stefanfoulis/django-filer/
 *
 * Copyright (c) 2010 Stefan Foulis
 *
 * BSD Licensed
 *
 */

(function($) {
	// jQuery plugin
	$.filebrowser = {
		defaults: {
			
		}
	};
	$.fn.filebrowser = function (opts) {
		return this.each(function() {
			var conf = $.extend({}, opts);
			if(conf !== false) new filebrowser_component().init(this, conf);
		});
	};
	function filebrowser_component() {
		return {
			cntr : ++filebrowser_component.cntr,
			settings: $.extend({},$filebrowser.defaults),
		};
	};

}