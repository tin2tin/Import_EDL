# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

bl_info = {
    "name": "Import EDL",
    "author": "Campbell Barton",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "Sequencer -> Track View Properties",
    "description": "Load a CMX formatted EDL into the sequencer",
    "warning": "",
    "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.6/Py/"
                "Scripts/Import-Export/EDL_Import",
    "category": "Import-Export",
}

import bpy


from bpy.props import (
        StringProperty,
        IntProperty,
        PointerProperty,
        )
from bpy.types import Operator

# ----------------------------------------------------------------------------
# Panel to show EDL Import UI

class SEQUENCER_PT_import_edl(bpy.types.Panel):
    """Path to an CMX 3600 EDL(.edl) file"""
    bl_label = "EDL Import"
    bl_space_type = 'SEQUENCE_EDITOR'
    bl_region_type = 'UI'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        scene = context.scene
        edl_import_info = scene.edl_import_info

        col = layout.column()
        #col.prop(edl_import_info, "frame_offset")
        col.prop(edl_import_info, "filepath", text="EDL File")
        
        subcol = layout.column()
        subcol.operator(ReloadEDL.bl_idname, text="Check For Missing Files")
        if not edl_import_info.filepath == "":
            subcol.enabled = True
        else:
            subcol.enabled = False

        box = layout.box()
        reel = None
        for reel in scene.edl_import_info.reels:
            col = box.column(align=True)
            if reel.filepath == "":
                col.prop(reel, "filepath", text="Missing: "+reel.name)
            else:
                col.prop(reel, "filepath", text="Found: "+reel.name)

        if reel is None:
            col = layout.column(align=True)
            col.operator(ImportEDL.bl_idname)
            col.enabled = False
        else:
            box.enabled = True
            box.operator(FindReelsEDL.bl_idname)
            layout.operator(ImportEDL.bl_idname)


# ----------------------------------------------------------------------------
# Main Operators


class ReloadEDL(Operator):
    """Reloads the EDL file and refreshes all reels"""
    bl_idname = "sequencer.import_edl_refresh"
    bl_label = "Refresh Reels"

    def execute(self, context):
        import os
        from . import parse_edl

        scene = context.scene
        edl_import_info = scene.edl_import_info

        filepath = edl_import_info.filepath
        dummy_fps = 25

        if not os.path.exists(filepath):
            self.report({'ERROR'}, "File Not Found %r" % filepath)
            return {'CANCELLED'}

        elist = parse_edl.EditList()
        if not elist.parse(filepath, dummy_fps):
            self.report({'ERROR'}, "Failed to parse EDL %r" % filepath)
            return {'CANCELLED'}

        scene = context.scene
        edl_import_info = scene.edl_import_info
        bl_reels = edl_import_info.reels

        data_prev = {reel.name: (reel.filepath, reel.frame_offset)
                     for reel in edl_import_info.reels}

        reels = elist.reels_as_dict()
        reels = [k for k in reels.keys() if k not in parse_edl.BLACK_ID]

        # re-create reels collection, keeping old values
        bl_reels.clear()
        for k in sorted(reels):
            reel = bl_reels.add()
            reel.name = k
            filepath, frame_offset = data_prev.get(k, (None, None))
            if filepath is not None:
                reel.filepath = filepath
                reel.frame_offset = frame_offset

        return {'FINISHED'}


class FindReelsEDL(Operator):
    """Scan a path for missing reel files, """ \
    """ Matching by reel name and existing filename when set"""
    bl_idname = "sequencer.import_edl_findreel"
    bl_label = "Scan For Missing Files"
    directory: StringProperty(
            subtype='DIR_PATH',
            )

    @staticmethod
    def missing_reels(context):
        import os
        scene = context.scene
        edl_import_info = scene.edl_import_info
        return [reel for reel in edl_import_info.reels
                if not os.path.exists(reel.filepath)]

    def execute(self, context):
        import os

        # walk over .avi, .mov, .wav etc.
        def media_file_walker(path):
            ext_check = bpy.path.extensions_movie | bpy.path.extensions_audio
            for dirpath, dirnames, filenames in os.walk(path):
                # skip '.git'
                dirnames[:] = [d for d in dirnames if not d.startswith(".")]
                for filename in filenames:
                    fileonly, ext = os.path.splitext(filename)
                    ext_lower = ext.lower()
                    if ext_lower in ext_check:
                        yield os.path.join(dirpath, filename), fileonly

        # scene = context.scene
        # edl_import_info = scene.edl_import_info

        bl_reels = FindReelsEDL.missing_reels(context)
        assert(len(bl_reels))

        # Search is as follows
        # Each reel has a triple:
        #    ([search_names, ...], [(priority, found_file), ...], bl_reel)
        bl_reels_search = [(set(), [], reel) for reel in bl_reels]

        # first get the search names...
        for reel_names, reel_files_found, reel in bl_reels_search:
            reel_names_list = []
            reel_names_list.append(reel.name.lower())

            # add non-extension version of the reel name
            if "." in reel_names_list[-1]:
                reel_names_list.append(os.path.splitext(reel_names_list[-1])[0])

            # use the filepath if set
            reel_filepath = reel.filepath
            if reel_filepath:
                reel_filepath = os.path.basename(reel_filepath)
                reel_filepath = os.path.splitext(reel_filepath)[0]
                reel_names_list.append(reel_filepath.lower())

            # when '_' are found, replace with space
            reel_names_list += [reel_filepath.replace("_", " ")
                                for reel_filepath in reel_names_list
                                if "_" in reel_filepath]
            reel_names.update(reel_names_list)

        # debug info
        print("Searching or %d reels" % len(bl_reels_search))
        for reel_names, reel_files_found, reel in bl_reels_search:
            print("Reel: %r --> (%s)" % (reel.name, " ".join(sorted(reel_names))))
        print()

        for filename, fileonly in media_file_walker(self.directory):
            for reel_names, reel_files_found, reel in bl_reels_search:
                if fileonly.lower() in reel_names:
                    reel_files_found.append((0, filename))
                else:
                    # check on partial match
                    for r in reel_names:
                        if fileonly.startswith(r):
                            reel_files_found.append((1, filename))
                        if fileonly.endswith(r):
                            reel_files_found.append((2, filename))

        # apply back and report
        tot_done = 0
        tot_fail = 0
        for reel_names, reel_files_found, reel in bl_reels_search:
            if reel_files_found:
                # make sure partial matches end last
                reel_files_found.sort()
                reel.filepath = reel_files_found[0][1]
                tot_done += 1
            else:
                tot_fail += 1

        self.report({'INFO'} if tot_fail == 0 else {'WARNING'},
                    "Found %d clips, missing %d" % (tot_done, tot_fail))

        return {'FINISHED'}

    def invoke(self, context, event):
        import os
        scene = context.scene
        edl_import_info = scene.edl_import_info

        if not FindReelsEDL.missing_reels(context):
            self.report({'INFO'},
                        "Nothing to do, all reels point to valid files")
            return {'CANCELLED'}

        # default to the EDL path
        if not self.directory and edl_import_info.filepath:
            self.directory = os.path.dirname(edl_import_info.filepath)

        wm = context.window_manager
        wm.fileselect_add(self)
        return {"RUNNING_MODAL"}


class ImportEDL(Operator):
    """Import an EDL file into the sequencer"""
    bl_idname = "sequencer.import_edl"
    bl_label = "Import Video Sequence"

    def execute(self, context):
        import os
        from . import import_edl
        scene = context.scene
        edl_import_info = scene.edl_import_info

        filepath = edl_import_info.filepath
        reel_filepaths = {reel.name: reel.filepath
                          for reel in edl_import_info.reels}
        reel_offsets = {reel.name: reel.frame_offset
                        for reel in edl_import_info.reels}

        if not os.path.exists(filepath):
            self.report({'ERROR'}, "File Not Found %r" % filepath)
            return {'CANCELLED'}

        msg = import_edl.load_edl(
                scene, filepath,
                reel_filepaths, reel_offsets,
                edl_import_info.frame_offset)

        if msg:
            self.report({'WARNING'}, msg)

        return {'FINISHED'}


# ----------------------------------------------------------------------------
# Persistent Scene Data Types (store EDL import info)

class EDLReelInfo(bpy.types.PropertyGroup):
    name: StringProperty(
            name="Name",
            )
    filepath: StringProperty(
            name="Video File",
            subtype='FILE_PATH',
            )
    frame_offset: IntProperty(
            name="Frame Offset",
            )


class EDLImportInfo(bpy.types.PropertyGroup):
    filepath: StringProperty(
            subtype='FILE_PATH',
            )
    reels: bpy.props.CollectionProperty(
            type=EDLReelInfo,
            )
    frame_offset: IntProperty(
            name="Global Frame Offset",
            )


def register():
    bpy.utils.register_class(ReloadEDL)
    bpy.utils.register_class(FindReelsEDL)
    bpy.utils.register_class(ImportEDL)
    bpy.utils.register_class(SEQUENCER_PT_import_edl)

    # edl_import_info
    bpy.utils.register_class(EDLReelInfo)
    bpy.utils.register_class(EDLImportInfo)
    bpy.types.Scene.edl_import_info = PointerProperty(type=EDLImportInfo)
    bpy.types.Scene.edl_reel_info = PointerProperty(type=EDLReelInfo)


def unregister():
    bpy.utils.unregister_class(ReloadEDL)
    bpy.utils.unregister_class(FindReelsEDL)
    bpy.utils.unregister_class(ImportEDL)
    bpy.utils.unregister_class(SEQUENCER_PT_import_edl)

    # edl_import_info
    bpy.utils.unregister_class(EDLImportInfo)
    bpy.utils.unregister_class(EDLReelInfo)
    del bpy.types.Scene.edl_import_info
    del bpy.types.Scene.edl_reel_info
