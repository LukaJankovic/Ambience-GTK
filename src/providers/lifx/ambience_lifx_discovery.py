# ambience_lifx_discovery.py
#
# Copyright 2021 Luka Jankovic
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk, Gdk, GLib, GObject, Handy
import threading, json

@Gtk.Template(resource_path='/io/github/lukajankovic/ambience/ambience_lifx_discovery.ui')
class AmbienceLIFXDiscovery(Gtk.Dialog):
    __gtype_name__ = 'AmbienceLIFXDiscovery'

    list_box = Gtk.Template.Child()
    reload_stack = Gtk.Template.Child()
    lan = None

    def __init__(self, lan, **kwargs):
        super().__init__(**kwargs)
        self.lan = lan

        self.reload(self)

    def clear_list(self):
        for widget in self.list_box.get_children():
            self.list_box.remove(widget)

    @Gtk.Template.Callback("reload")
    def reload(self, sender):
        self.clear_list()
        self.reload_stack.set_visible_child_name("loading")
        self.init_discovery()

    def init_discovery(self):
        """
        Initialize discovery thread. Starts spinner etc.
        """
        discovery_thread = threading.Thread(target=self.discovery)
        discovery_thread.daemon = True
        discovery_thread.start()

    def discovery(self):
        """
        Discovery thread.
        """

        self.lights = self.lan.get_lights()

        for light in self.lights:
            light.label = fetch_data_sync(light.get_label)
            light.mac = fetch_data_sync(light.get_mac_addr)

            if not light.label or not light.mac:
                self.lights.remove(light)

        GLib.idle_add(self.update_list)

    def update_list(self):
        config_list = get_config(get_dest_file())

        for light in self.lights:
            sidebar_item = DiscoveryItem()
            sidebar_item.light = light
            sidebar_item.light_label.set_text(light.label)
            sidebar_item.dest_file = get_dest_file()
            sidebar_item.config_list = config_list

            done = False
            for group in config_list["groups"]:
                for saved_light in group["lights"]:
                    if saved_light["mac"] == light.mac:
                        sidebar_item.added = True
                        sidebar_item.update_icon()
                        done = True
                        break

                if done:
                    break

            self.list_box.insert(sidebar_item, -1)

        self.reload_stack.set_visible_child_name("button")