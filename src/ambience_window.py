# ambience_window.py
#
# Copyright 2022 Luka Jankovic
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

from struct import error
import threading

from gi.repository import Gtk, Gdk, GLib, Handy
from .ambience_loader import *

from .ambience_discovery import AmbienceDiscovery

from ambience.widgets.ambience_flow_box import AmbienceFlowBox
from ambience.widgets.ambience_group_tile import AmbienceGroupTile
from ambience.widgets.ambience_light_tile import AmbienceLightTile

from ambience.views.ambience_group_control import AmbienceGroupControl
from ambience.views.ambience_light_control import AmbienceLightControl

import threading

@Gtk.Template(resource_path='/io/github/lukajankovic/ambience/ambience_window.ui')
class AmbienceWindow(Handy.ApplicationWindow):
    """
    Controls almost every aspect of the main window, including maintaining
    a list of lights and controling them.
    """
    __gtype_name__ = 'AmbienceWindow'

    main_popover = Gtk.Template.Child()
    main_leaflet = Gtk.Template.Child()

    title_label = Gtk.Template.Child()
    group_label_stack = Gtk.Template.Child()
    group_label_edit = Gtk.Template.Child()
    group_label_entry = Gtk.Template.Child()

    menu_box = Gtk.Template.Child()
    header_bar = Gtk.Template.Child()
    sidebar = Gtk.Template.Child()

    group_header_bar = Gtk.Template.Child()
    back = Gtk.Template.Child()

    controls_deck = Gtk.Template.Child()
    tiles_box = Gtk.Template.Child()

    loading_stack = Gtk.Template.Child()
    tiles_list = Gtk.Template.Child()

    tiles_spinner = Gtk.Template.Child()

    new_group_popover = Gtk.Template.Child()
    new_group_entry = Gtk.Template.Child()
    new_group_button = Gtk.Template.Child()

    invalid_name = Gtk.Template.Child()

    devices_button = Gtk.Template.Child()

    group_labels = []

    def create_header_label(self):
        """
        Returns a GtkLabel suitable to be used as a header in the tiles list.
        """
        label = Gtk.Label()
        label.get_style_context().add_class("title-3")
        label.set_visible(True)
        label.set_margin_start(6)
        label.set_margin_end(6)
        label.set_margin_top(6)
        label.set_margin_bottom(6)
        label.set_alignment(0, 0)

        return label

    @Gtk.Template.Callback("notify_fold_cb")
    def notify_fold_cb(self, sender, user_data):
        """
        Window switched between normal and mobile (folded) state.
        """
        if sender.get_folded():
            self.back.show_all()
        else:
            self.back.hide()

        self.header_bar.set_show_close_button(sender.get_folded())

    @Gtk.Template.Callback("notify_main_visible_child_name")
    def notify_visible_child_name(self, sender, user_data):
        if sender.get_visible_child_name() == "menu":
            self.go_back(sender)
            self.clear_tiles()

    @Gtk.Template.Callback("notify_controls_visible_child_name")
    def visible_child_name_changed(self, sender, user_data):
        if self.controls_deck.get_visible_child_name() == "tiles":

            def wait_finished():
                self.sidebar_selected(self, None)

            def wait_thread():
                while self.controls_deck.get_transition_running():
                    pass
                GLib.idle_add(lambda: self.sidebar_selected(self, None))

            t = threading.Thread(target=wait_thread)
            t.start()

    @Gtk.Template.Callback("go_back")
    def go_back(self, sender):
        """
        Back button pressed. Goes back to group list.
        """
        self.sidebar.unselect_all()
        self.main_leaflet.set_visible_child(self.menu_box)

    @Gtk.Template.Callback("sidebar_selected")
    def sidebar_selected(self, sender, user_data):
        """
        Group in sidebar selected by user.
        """

        if not self.sidebar.get_selected_row():
            self.clear_tiles()
            return

        self.clear_controls()
        self.clear_tiles()

        self.devices_button.set_visible(True)
        self.group_label_edit.set_visible(True)

        tile_size_group = Gtk.SizeGroup()
        tile_size_group.set_mode(Gtk.SizeGroupMode.HORIZONTAL)

        self.active_group = self.sidebar.get_selected_row().group

        self.title_label.set_text(self.active_group.label)

        all_category = AmbienceFlowBox()
        all_tile = AmbienceGroupTile(self.active_group)
        all_tile.clicked_callback = self.group_edit

        tile_size_group.add_widget(all_tile)
        all_category.insert(all_tile, -1)

        self.tiles_list.add(all_category)

        def create_category(lights, title, offline=False):
            lights_label = self.create_header_label()
            lights_label.set_text(title)

            self.tiles_list.add(lights_label)

            lights_category = AmbienceFlowBox()

            for light in lights:
                light_tile = AmbienceLightTile(light, self.tile_clicked)
                tile_size_group.add_widget(light_tile)
                lights_category.insert(light_tile, -1)

                if offline:
                    light_tile.set_sensitive(False)

            self.tiles_list.add(lights_category)

        online = []
        offline = []
        for device in self.active_group.devices:
            if device.get_online():
                online.append(device)
            else:
                offline.append(device)

        if len(online) > 0:
            create_category(online, "Lights")

        if len(offline) > 0:
            create_category(offline, "Offline")

        self.main_leaflet.set_visible_child(self.controls_deck)

    def clear_controls(self):
        """
        Removes control views from deck.
        """
        self.controls_deck.set_visible_child_name("tiles")
        for child in self.controls_deck.get_children()[1:]:
            self.controls_deck.remove(child)

    def clear_sidebar(self):
        """
        Empties the sidebar.
        """

        for sidebar_item in self.sidebar.get_children():
            self.sidebar.remove(sidebar_item)

    def clear_tiles(self):
        """
        Empties the main view from tiles, headers, etc.
        """

        for group_item in self.tiles_list.get_children():
            self.tiles_list.remove(group_item)

    @Gtk.Template.Callback("create_group")
    def create_group(self, sender):
        label = self.new_group_entry.get_text()
        group = AmbienceLoader().get_group(label)
        group_item = self.create_group_item(group)
        self.sidebar.insert(group_item, -1)

        self.new_group_popover.popdown()
        self.group_labels.append(label)
        self.new_group_entry.set_text("")

    @Gtk.Template.Callback("new_group_entry_changed")
    def new_group_entry_changed(self, sender):
        if self.new_group_entry.get_text() in self.group_labels:
            self.new_group_button.set_sensitive(False) 
            self.invalid_name.set_reveal_child(True)
        else:
            self.new_group_button.set_sensitive(True)
            self.invalid_name.set_reveal_child(False)

    @Gtk.Template.Callback("toggle_edit")
    def toggle_edit(self, sender):
        self.deselect_sidebar()

        if sender.get_active():
            self.header_bar.get_style_context().add_class("selection-mode")
            self.group_header_bar.get_style_context().add_class("selection-mode")

            self.sidebar.set_selection_mode(Gtk.SelectionMode.NONE)

            for row in self.sidebar.get_children():

                def delete_action(sender):

                    title = sender.row.get_title()

                    def perform_delete(_, response):
                        if response == Gtk.ResponseType.YES:
                            AmbienceLoader().delete_group(sender.row.group)
                            self.group_labels.remove(title)
                            self.sidebar.remove(sender.row)

                    confirm_dialog = Gtk.MessageDialog(self,
                                                        0,
                                                        Gtk.MessageType.WARNING,
                                                        Gtk.ButtonsType.NONE,
                                                        f"Are you sure you want to delete the group “{title}”?"
                    )
                    confirm_dialog.format_secondary_text(
                        "This action cannot be reversed."
                    )

                    confirm_dialog.add_button("_Cancel", Gtk.ResponseType.CLOSE)
                    confirm_dialog.add_button("_Delete", Gtk.ResponseType.YES)

                    confirm_dialog.get_widget_for_response(Gtk.ResponseType.YES).get_style_context().add_class("destructive-action")
                    confirm_dialog.get_widget_for_response(Gtk.ResponseType.YES).get_style_context().add_class("default")

                    confirm_dialog.connect("response", perform_delete)

                    confirm_dialog.run()
                    confirm_dialog.destroy()

                delete_icon = Gtk.Image.new_from_icon_name("process-stop-symbolic", 1)
                delete_icon.set_visible(True)

                delete_button = Gtk.Button()
                delete_button.row = row
                delete_button.add(delete_icon)
                delete_button.get_style_context().add_class("destructive-action")
                delete_button.set_valign(Gtk.Align.CENTER)
                delete_button.connect("clicked", delete_action)
                delete_button.set_visible(True)

                row.add(delete_button)
        else:
            self.header_bar.get_style_context().remove_class("selection-mode")
            self.group_header_bar.get_style_context().remove_class("selection-mode")

            self.sidebar.set_selection_mode(Gtk.SelectionMode.SINGLE)

            for row in self.sidebar.get_children():
                for c in row.get_children():
                    row.remove(c)

    def deselect_sidebar(self):
        self.clear_tiles()
        self.title_label.set_text("")
        self.sidebar.unselect_all()

        self.devices_button.set_visible(False)
        self.group_label_edit.set_visible(False)

    @Gtk.Template.Callback("manage_devices")
    def manage_devices(self, sender):

        def discovery_done(sender, user_data):
            self.sidebar_selected(self, None)

        discovery_window = AmbienceDiscovery(transient_for=self, modal=True, use_header_bar=1)
        discovery_window.group = self.active_group
        discovery_window.connect("response", discovery_done)
        discovery_window.show_all()

    def reload(self, sender):
        """
        Reloads data from config file and populates sidebar.
        """
        self.clear_tiles()
        self.clear_sidebar()

        for group in AmbienceLoader().get_all_groups():
            group_item = self.create_group_item(group)
            self.group_labels.append(group_item.get_title()) 
            self.sidebar.insert(group_item, -1)

    def create_group_item(self, group):
        group_item = Handy.ActionRow()
        group_item.set_visible(True)
        group_item.set_title(group.get_label())
        group_item.set_can_focus(False)
        group_item.group = group

        return group_item

    def reload_group_name(self):
        self.title_label.set_text(self.active_group.get_label())
        self.sidebar.get_selected_row().set_title(self.active_group.get_label())

    def group_label_valid(self, text):
        return text and not (text in self.group_labels and text != self.active_group.get_label())

    @Gtk.Template.Callback("group_label_edit_toggled")
    def group_label_edit_toggled(self, sender):
        if sender.get_active():
            self.group_label_entry.set_text(self.active_group.get_label())
            self.group_label_entry.grab_focus()

            self.group_label_stack.set_visible_child_name("edit")
        else:
            text = self.group_label_entry.get_text()
            if self.group_label_valid(text):
                self.group_labels.remove(self.active_group.get_label())
                self.active_group = AmbienceLoader().rename_group(self.active_group, text)
                self.group_labels.append(self.active_group.get_label())
                self.reload_group_name()

                self.group_label_stack.set_visible_child_name("label")

    @Gtk.Template.Callback("group_edit_event")
    def group_edit_event(self, sender, event):
        if event.keyval == Gdk.KEY_Escape:
            self.group_label_entry.set_text(self.active_group.get_label())
            self.group_label_edit.set_active(False)

    @Gtk.Template.Callback("group_label_changed")
    def group_label_changed(self, sender):
        self.group_label_edit.set_sensitive(self.group_label_valid(self.group_label_entry.get_text()))

    @Gtk.Template.Callback("group_label_activate")
    def group_label_activate(self, sender):
        if self.group_label_valid(self.group_label_entry.get_text()):
            self.group_label_edit.set_active(False)

    # Light control

    def tile_clicked(self, tile):
        """
        Runs when a tile gets clicked. Switches to the light control page.
        """
        light_controls = AmbienceLightControl(tile.light,
                                              self.controls_deck,
                                              self.light_control_exit)
        light_controls.set_visible(True)

        self.controls_deck.insert_child_after(light_controls, self.tiles_box)
        self.controls_deck.navigate(Handy.NavigationDirection.FORWARD)
        light_controls.show()

    def group_edit(self, tile):
        group_controls = AmbienceGroupControl(tile.group,
                                              self.controls_deck,
                                              self.light_control_exit)

        group_controls.set_visible(True)

        self.controls_deck.insert_child_after(group_controls, self.tiles_box)
        self.controls_deck.navigate(Handy.NavigationDirection.FORWARD)
        group_controls.show()

    def light_control_exit(self, controls):
        self.controls_deck.navigate(Handy.NavigationDirection.BACK)

    # Group management
    def get_group_value(self, prop):
        value = -1
        for light in self.online:
            if value == -1:
                value = light.__dict__[prop]
            elif not value == light.__dict__[prop]:
                break

        if value == -1:
            return None
        return value

    # Initialization, startup

    def __init__(self, lan, **kwargs):
        super().__init__(**kwargs)
        self.reload(self)
