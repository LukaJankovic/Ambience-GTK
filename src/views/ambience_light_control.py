# ambience_light_control.py
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

from gi.repository import Gtk, Gdk

from ambience.model.ambience_light import AmbienceLightCapabilities
from ambience.model.ambience_device import AmbienceDeviceInfoType

@Gtk.Template(resource_path='/io/github/lukajankovic/ambience/ambience_light_control.ui')
class AmbienceLightControl(Gtk.Box):
    __gtype_name__ = 'AmbienceLightControl'

    main_stack = Gtk.Template.Child()

    hue_row = Gtk.Template.Child()
    saturation_row = Gtk.Template.Child()
    kelvin_row = Gtk.Template.Child() 
    infrared_row = Gtk.Template.Child()

    hue_scale = Gtk.Template.Child()
    saturation_scale = Gtk.Template.Child()
    brightness_scale = Gtk.Template.Child()
    kelvin_scale = Gtk.Template.Child()
    kelvin_adj = Gtk.Template.Child()
    infrared_scale = Gtk.Template.Child()

    model_row = Gtk.Template.Child()
    model_label = Gtk.Template.Child()

    ip_row = Gtk.Template.Child()
    ip_label = Gtk.Template.Child()

    group_row = Gtk.Template.Child()
    group_label = Gtk.Template.Child()

    location_row = Gtk.Template.Child()
    location_label = Gtk.Template.Child()

    edit = Gtk.Template.Child()
    edit_stack = Gtk.Template.Child()
    light_edit_label = Gtk.Template.Child()

    power_switch = Gtk.Template.Child()

    light_label = Gtk.Template.Child()

    light = None
    deck = None
    back_callback = None
    update_active = False

    def __init__(self, light, deck, back_callback, **kwargs):
        self.light = light
        self.deck = deck
        self.back_callback = back_callback

        super().__init__(**kwargs)

    def show(self):
        """
        The view is ready to show. Update rows.
        """
        self.update_rows()

    def update_rows(self):
        self.update_active = True

        self.light_label.set_label(self.light.get_label())
        self.power_switch.set_active(self.light.get_power())

        (hue, saturation, brightness, kelvin) = self.light.get_color()

        self.brightness_scale.set_value(brightness * 100)

        capabilities = self.light.get_capabilities()

        if AmbienceLightCapabilities.COLOR in capabilities: 
            self.hue_row.set_visible(True)
            self.saturation_row.set_visible(True)

            self.hue_scale.set_value(hue * 365)
            self.saturation_scale.set_value(saturation * 100)

        if AmbienceLightCapabilities.TEMPERATURE in capabilities:
            self.kelvin_row.set_visible(True)
            self.kelvin_scale.set_value(kelvin)

        if AmbienceLightCapabilities.INFRARED in capabilities:
            self.infrared_row.set_visible(True)
            self.infrared_scale.set_value(self.light.get_infrared())

        self.update_active = False

        info = self.light.get_info()

        rows = {
            AmbienceDeviceInfoType.MODEL    : self.model_row,
            AmbienceDeviceInfoType.IP       : self.ip_row,
            AmbienceDeviceInfoType.GROUP    : self.group_row,
            AmbienceDeviceInfoType.LOCATION : self.location_row
        }

        labels = {
            AmbienceDeviceInfoType.MODEL    : self.model_label,
            AmbienceDeviceInfoType.IP       : self.ip_label,
            AmbienceDeviceInfoType.GROUP    : self.group_label,
            AmbienceDeviceInfoType.LOCATION : self.location_label
        }

        for type in AmbienceDeviceInfoType:
            if type in info.keys():
                rows[type].set_visible(True)
                labels[type].set_text(info[type])
 
    @Gtk.Template.Callback("push_color")
    def push_color(self, sender):
        """
        Color data changed by the user, push it to the bulb.
        """
        if self.update_active:
            return

        hue = self.hue_scale.get_value()
        saturation = self.saturation_scale.get_value()
        brightness = self.brightness_scale.get_value()
        kelvin = self.kelvin_scale.get_value()

        self.light.set_color([hue / 365, saturation / 100, brightness / 100, kelvin])

        if AmbienceLightCapabilities.INFRARED in self.light.get_capabilities():
            self.light.set_infrared(self.infrared_scale.get_value() * 100)

    @Gtk.Template.Callback("set_light_power")
    def set_light_power(self, sender, user_data):
        self.light.set_power(sender.get_active())

    # Editing label

    @Gtk.Template.Callback("name_changed")
    def name_changed(self, sender):
        """
        Checks to see if the edit toggle button should be disabled if the name
        is empty.
        """
        self.edit.set_sensitive(self.light_edit_label.get_text())

    @Gtk.Template.Callback("name_activate")
    def name_enter(self, sender):
        """
        Perform the same action as when toggling the edit button.
        """

        if self.edit.get_active():
            self.edit.set_active(False)

    @Gtk.Template.Callback("name_event")
    def name_event(self, sender, event):
        """
        User cancelled edit label event.
        """

        if event.keyval == Gdk.KEY_Escape:
            self.light_edit_label.set_text(self.light.label)
            self.edit.set_active(False)

    @Gtk.Template.Callback("do_edit")
    def do_edit(self, sender):
        """
        Toggle edit label mode.
        """
        if self.edit.get_active():
            self.light_edit_label.set_text(self.light.label)
            self.edit_stack.set_visible_child_name("editing")
        else:
            new_label = self.light_edit_label.get_text()

            self.edit_stack.set_visible_child_name("normal")

            self.light.set_label(new_label)
            self.light.label = new_label
            self.light_label.set_text(new_label)

    @Gtk.Template.Callback("go_back")
    def go_back(self, sender):
        self.back_callback(self)