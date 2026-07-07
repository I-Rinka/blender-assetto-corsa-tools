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
#
# Copyright (C) 2014  Thomas Hagnhofer


import os
import tempfile

import bpy

from .kn5_writer import KN5Writer
from .exporter_utils import get_all_texture_nodes


DDS_HEADER_BYTES = b"DDS"


class TextureWriter(KN5Writer):
    def __init__(self, file, context, warnings):
        super().__init__(file)

        self.available_textures = {}
        self.texture_positions = {}
        self.warnings = warnings
        self.context = context
        self._fill_available_image_textures()

    def write(self):
        self.write_int(len(self.available_textures))
        for texture_name, _position in sorted(self.texture_positions.items(), key=lambda k: k[1]):
            self._write_texture(self.available_textures[texture_name])

    def _write_texture(self, texture):
        is_active = 1
        self.write_int(is_active)
        self.write_string(texture.image.name)
        image_data = self._get_image_data_from_texture(texture)
        self.write_blob(image_data)

    def _fill_available_image_textures(self):
        self.available_textures = {}
        self.texture_positions = {}
        position = 0

        all_texture_nodes = get_all_texture_nodes(self.context)
        for texture_node in all_texture_nodes:
            if not texture_node.name.startswith("__"):
                if not texture_node.image:
                    self.warnings.append(f"Ignoring texture node without image '{texture_node.name}'")
                elif not texture_node.image.pixels:
                    self.warnings.append(f"Ignoring texture node without image data '{texture_node.name}'")
                else:
                    self.available_textures[texture_node.image.name] = texture_node
                    self.texture_positions[texture_node.image.name] = position
                    position += 1

    def _get_image_data_from_texture(self, texture):
        image_copy = texture.image.copy()
        try:
            # If the image is already packed, use the packed data directly
            if image_copy.packed_file:
                image_data = image_copy.packed_file.data
                image_header_magic_bytes = image_data[:3]
                # Check if it's DDS data
                if image_header_magic_bytes == DDS_HEADER_BYTES:
                    return image_data
                # For non-DDS packed data, check if the original format is PNG
                if image_copy.file_format == "PNG":
                    return image_data
                # Packed JPEG or other format - convert to PNG
                return self._convert_image_to_png(image_copy)

            # Image is not packed - try to pack it
            if image_copy.file_format in ("PNG", "DDS", ""):
                self._safe_pack(image_copy)
                image_data = image_copy.packed_file.data
                image_header_magic_bytes = image_data[:3]
                if image_copy.file_format != "" or image_header_magic_bytes == DDS_HEADER_BYTES:
                    return image_data
            return self._convert_image_to_png(image_copy)
        finally:
            self.context.blend_data.images.remove(image_copy)

    def _safe_pack(self, image):
        """Pack image data, handling missing source files by saving to temp first."""
        filepath = bpy.path.abspath(image.filepath)
        if os.path.exists(filepath):
            image.pack()
        else:
            # Source file missing - save pixel data to a temp file, then pack
            ext = os.path.splitext(image.name)[1].lower()
            if ext == '.dds':
                tmp_name = image.name
                image.file_format = 'DDS'
            else:
                tmp_name = os.path.splitext(image.name)[0] + '.png'
                image.file_format = 'PNG'
            tmp_path = os.path.join(tempfile.gettempdir(), tmp_name)
            image.filepath_raw = tmp_path
            image.save()
            image.pack()

    def _convert_image_to_png(self, image):
        # If already packed, save to temp file to get PNG data
        tmp_name = os.path.splitext(image.name)[0] + '.png'
        tmp_path = os.path.join(tempfile.gettempdir(), tmp_name)
        image.filepath_raw = tmp_path
        image.file_format = 'PNG'
        image.save()
        image.pack()
        return image.packed_file.data
